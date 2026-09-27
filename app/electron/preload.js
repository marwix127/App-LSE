const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("signcam", {
  start: (config) => ipcRenderer.invoke("sidecar:start", config),
  stop: () => ipcRenderer.invoke("sidecar:stop"),
  listCameras: () => ipcRenderer.invoke("cameras:list"),
  // devuelve la función para desuscribirse
  onEvent: (callback) => {
    const handler = (_e, evento) => callback(evento);
    ipcRenderer.on("sidecar:event", handler);
    return () => ipcRenderer.removeListener("sidecar:event", handler);
  },
});
