const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("nirmiqDesktop", {
  getStatus: () => ipcRenderer.invoke("nirmiq:status"),
  restartRuntime: () => ipcRenderer.invoke("nirmiq:restart"),
});
