const { contextBridge, ipcRenderer } = require("electron");

// API segura expuesta al renderer (React) como window.signcam
contextBridge.exposeInMainWorld("signcam", {
  start: (config) => ipcRenderer.invoke("sidecar:start", config),
  stop: () => ipcRenderer.invoke("sidecar:stop"),
  listCameras: () => ipcRenderer.invoke("cameras:list"),
  // Suscripción a eventos del sidecar. Devuelve función para desuscribir.
  onEvent: (callback) => {
    const handler = (_e, evento) => callback(evento);
    ipcRenderer.on("sidecar:event", handler);
    return () => ipcRenderer.removeListener("sidecar:event", handler);
  },
});
