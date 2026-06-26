const { app, BrowserWindow, ipcMain, session } = require("electron");
const { spawn, execFile } = require("child_process");
const readline = require("readline");
const path = require("path");

const DEV = process.env.SIGNCAM_DEV === "1";
// Raíz del proyecto Python (un nivel por encima de app/).
const PROJECT_ROOT = path.resolve(__dirname, "..", "..");
const PYTHON = path.join(PROJECT_ROOT, "venv", "Scripts", "python.exe");
const SIDECAR = path.join(PROJECT_ROOT, "signcam_sidecar.py");
const LISTAR_CAMARAS = path.join(PROJECT_ROOT, "listar_camaras.py");

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

  const args = [
    "-u", // sin buffering: los eventos JSON llegan al instante
    SIDECAR,
    "--camera", String(config.camera ?? 0),
    "--subtitle-scale", String(config.subtitleScale ?? 1.0),
    "--subtitle-position", config.subtitlePosition ?? "bottom",
  ];

  sidecar = spawn(PYTHON, args, { cwd: PROJECT_ROOT });

  // stdout = eventos JSON, una línea por evento.
  readline.createInterface({ input: sidecar.stdout }).on("line", (linea) => {
    const txt = linea.trim();
    if (!txt) return;
    try {
      enviar(JSON.parse(txt));
    } catch {
      enviar({ type: "log", message: txt });
    }
  });

  // stderr = warnings de TF/MediaPipe; los mandamos como log para depurar.
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
  // taskkill /T /F mata el proceso y sus hijos aunque esté colgado en COM
  // (un kill normal no puede con un proceso "Not Responding").
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
  // Si está bloqueado y no sale en 2s, forzar cierre del árbol de procesos.
  setTimeout(() => {
    if (proc && !proc.killed) matarArbol(pid);
  }, 2000);
}

ipcMain.handle("cameras:list", () => {
  return new Promise((resolve) => {
    let salida = "";
    const p = spawn(PYTHON, [LISTAR_CAMARAS], { cwd: PROJECT_ROOT });
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
  // Permitir acceso a la cámara (necesario para getUserMedia y enumerar dispositivos).
  session.defaultSession.setPermissionRequestHandler((_wc, _perm, cb) => cb(true));
  // setPermissionCheckHandler concede el permiso de forma síncrona, así
  // enumerateDevices() devuelve las ETIQUETAS sin tener que abrir antes una cámara.
  session.defaultSession.setPermissionCheckHandler(() => true);
  createWindow();
});

app.on("window-all-closed", () => {
  pararSidecar();
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", pararSidecar);
