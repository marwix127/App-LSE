const { app, BrowserWindow, ipcMain, session } = require("electron");
const { spawn, execFile } = require("child_process");
const readline = require("readline");
const path = require("path");

const DEV = process.env.SIGNCAM_DEV === "1";
// raíz del proyecto (encima de app/)
const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const PYTHON = path.join(PROJECT_ROOT, "venv", "Scripts", "python.exe");
const SIDECAR = path.join(PROJECT_ROOT, "signcam_sidecar.py");
const SIDECAR_EXE = path.join(PROJECT_ROOT, "dist", "signcam_sidecar", "signcam_sidecar.exe");

// dev: python del venv, prod: el .exe de PyInstaller
function comandoSidecar(args) {
  if (DEV) return { cmd: PYTHON, args: ["-u", SIDECAR, ...args] };
  return { cmd: SIDECAR_EXE, args };
}

let win = null;
let sidecar = null;

function createWindow() {
  win = new BrowserWindow({
    width: 1100,
    height: 760,
    backgroundColor: "#0f1115",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (DEV) {
    win.loadURL("http://localhost:5173");
    win.webContents.openDevTools({ mode: "detach" });
  } else {
    win.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  win.on("closed", () => {
    win = null;
  });
}

function enviar(evento) {
  if (win && !win.isDestroyed()) win.webContents.send("sidecar:event", evento);
}

function arrancarSidecar(config = {}) {
  if (sidecar) return; // ya corriendo

  const { cmd, args } = comandoSidecar([
    "--camera", String(config.camera ?? 0),
    "--subtitle-scale", String(config.subtitleScale ?? 1.0),
    "--subtitle-position", config.subtitlePosition ?? "bottom",
  ]);

  sidecar = spawn(cmd, args, { cwd: PROJECT_ROOT, windowsHide: true });

  // stdout: un evento JSON por línea
  readline.createInterface({ input: sidecar.stdout }).on("line", (linea) => {
    const txt = linea.trim();
    if (!txt) return;
    try {
      enviar(JSON.parse(txt));
    } catch {
      enviar({ type: "log", message: txt });
    }
  });

  // stderr se manda como log
  readline.createInterface({ input: sidecar.stderr }).on("line", (linea) => {
    if (linea.trim()) enviar({ type: "log", message: linea.trim() });
  });

  sidecar.on("exit", (code) => {
    enviar({ type: "exit", code });
    sidecar = null;
  });

  sidecar.on("error", (err) => {
    enviar({ type: "error", message: `No se pudo lanzar el sidecar: ${err.message}` });
    sidecar = null;
  });
}

function matarArbol(pid) {
  // si se queda colgado en COM un kill normal no lo cierra
  execFile("taskkill", ["/PID", String(pid), "/T", "/F"], () => {});
}

function pararSidecar() {
  if (!sidecar) return;
  const proc = sidecar;
  const pid = proc.pid;
  try {
    proc.stdin.write("stop\n");
  } catch {
    matarArbol(pid);
    return;
  }
  // si en 2 s no ha salido, se mata
  setTimeout(() => {
    if (proc && !proc.killed) matarArbol(pid);
  }, 2000);
}

ipcMain.handle("cameras:list", () => {
  return new Promise((resolve) => {
    let salida = "";
    const { cmd, args } = comandoSidecar(["--list-cameras"]);
    const p = spawn(cmd, args, { cwd: PROJECT_ROOT, windowsHide: true });
    p.stdout.on("data", (d) => (salida += d.toString()));
    p.on("error", () => resolve([]));
    p.on("close", () => {
      try {
        resolve(JSON.parse(salida).devices || []);
      } catch {
        resolve([]);
      }
    });
  });
});

ipcMain.handle("sidecar:start", (_e, config) => {
  arrancarSidecar(config);
  return true;
});

ipcMain.handle("sidecar:stop", () => {
  pararSidecar();
  return true;
});

app.whenReady().then(() => {
  // permisos de cámara para el preview
  session.defaultSession.setPermissionRequestHandler((_wc, _perm, cb) => cb(true));
  // sin esto enumerateDevices() devuelve las cámaras sin nombre
  session.defaultSession.setPermissionCheckHandler(() => true);
  createWindow();
});

app.on("window-all-closed", () => {
  pararSidecar();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", pararSidecar);
