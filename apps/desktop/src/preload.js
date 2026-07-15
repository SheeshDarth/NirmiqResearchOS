const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("nirmiqDesktop", {
  getStatus: () => ipcRenderer.invoke("nirmiq:status"),
  getStartupFailure: () => ipcRenderer.invoke("nirmiq:startup-failure"),
  openLogs: () => ipcRenderer.invoke("nirmiq:open-logs"),
  runDoctor: () => ipcRenderer.invoke("nirmiq:run-doctor"),
  retryStartup: () => ipcRenderer.invoke("nirmiq:retry-startup"),
  restartRuntime: () => ipcRenderer.invoke("nirmiq:restart"),
});
