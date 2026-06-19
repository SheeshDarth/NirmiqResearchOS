const { app, BrowserWindow, Menu, dialog, ipcMain, shell } = require("electron");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");
const { spawn } = require("node:child_process");

const ROOT_DIR = path.resolve(__dirname, "..", "..", "..");
const API_DIR = path.join(ROOT_DIR, "apps", "api");
const WEB_DIR = path.join(ROOT_DIR, "apps", "web");
const TEMP_DIR = path.join(ROOT_DIR, "temp", "desktop");
const API_URL = "http://127.0.0.1:8000";
const WEB_URL = "http://127.0.0.1:3002";
const API_HEALTH_URL = `${API_URL}/health`;

const isWindows = process.platform === "win32";
const npmCommand = isWindows ? "npm.cmd" : "npm";
const pythonCommand = isWindows ? "python" : "python3";

let mainWindow = null;
let apiProcess = null;
let webProcess = null;
let runtimeStarting = false;

function ensureRuntimeDir() {
  fs.mkdirSync(TEMP_DIR, { recursive: true });
}

function logPath(name) {
  ensureRuntimeDir();
  return path.join(TEMP_DIR, `${name}.log`);
}

function appendLog(name, line) {
  fs.appendFileSync(logPath(name), line);
}

function isPortOpen(port) {
  return new Promise((resolve) => {
    const socket = new net.Socket();
    socket.setTimeout(700);
    socket.once("connect", () => {
      socket.destroy();
      resolve(true);
    });
    socket.once("timeout", () => {
      socket.destroy();
      resolve(false);
    });
    socket.once("error", () => resolve(false));
    socket.connect(port, "127.0.0.1");
  });
}

function waitForUrl(url, timeoutMs) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    const attempt = () => {
      const request = http.get(url, (response) => {
        response.resume();
        if (response.statusCode && response.statusCode < 500) {
          resolve(true);
          return;
        }
        retry();
      });
      request.setTimeout(3000, () => {
        request.destroy();
        retry();
      });
      request.on("error", retry);
    };
    const retry = () => {
      if (Date.now() - startedAt > timeoutMs) {
        reject(new Error(`Timed out waiting for ${url}`));
        return;
      }
      setTimeout(attempt, 1200);
    };
    attempt();
  });
}

function spawnLoggedProcess(name, command, args, cwd, env = {}) {
  appendLog(name, `\n\n[${new Date().toISOString()}] starting: ${command} ${args.join(" ")}\n`);
  const child = spawn(command, args, {
    cwd,
    env: { ...process.env, ...env },
    windowsHide: true,
    shell: false,
  });
  child.stdout.on("data", (chunk) => appendLog(name, chunk.toString()));
  child.stderr.on("data", (chunk) => appendLog(name, chunk.toString()));
  child.on("exit", (code, signal) => {
    appendLog(name, `\n[${new Date().toISOString()}] exited code=${code} signal=${signal}\n`);
  });
  return child;
}

async function startRuntime() {
  if (runtimeStarting) return;
  runtimeStarting = true;
  ensureRuntimeDir();
  try {
    if (!(await isPortOpen(8000))) {
      apiProcess = spawnLoggedProcess(
        "api",
        pythonCommand,
        ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        API_DIR,
        {
          PYTHONPATH: API_DIR,
          LOW_MEMORY_MODE: "true",
        },
      );
    }

    if (!(await isPortOpen(3002))) {
      const hasBuild = fs.existsSync(path.join(WEB_DIR, ".next"));
      webProcess = spawnLoggedProcess("web", npmCommand, ["run", hasBuild ? "start" : "dev"], WEB_DIR);
    }

    await waitForUrl(API_HEALTH_URL, 60000);
    await waitForUrl(WEB_URL, 90000);
  } finally {
    runtimeStarting = false;
  }
}

function stopRuntime() {
  for (const child of [webProcess, apiProcess]) {
    if (child && !child.killed) {
      if (isWindows) {
        spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], { windowsHide: true });
      } else {
        child.kill();
      }
    }
  }
  webProcess = null;
  apiProcess = null;
}

async function restartRuntime() {
  stopRuntime();
  await startRuntime();
  if (mainWindow) {
    await mainWindow.loadURL(WEB_URL);
  }
}

function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 1100,
    minHeight: 740,
    title: "NIRMIQ ResearchOS Desktop",
    backgroundColor: "#111418",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  mainWindow.once("ready-to-show", () => mainWindow.show());
  mainWindow.loadURL(WEB_URL);
}

function openPath(targetPath) {
  shell.openPath(targetPath).then((error) => {
    if (error) {
      dialog.showErrorBox("NIRMIQ", error);
    }
  });
}

function openInVsCode() {
  const command = isWindows ? "cmd.exe" : "sh";
  const args = isWindows ? ["/c", "code", ROOT_DIR] : ["-lc", `code "${ROOT_DIR}"`];
  const child = spawn(command, args, { detached: true, stdio: "ignore", windowsHide: true });
  child.unref();
}

async function showRuntimeStatus() {
  const apiOpen = await isPortOpen(8000);
  const webOpen = await isPortOpen(3002);
  dialog.showMessageBox(mainWindow, {
    type: apiOpen && webOpen ? "info" : "warning",
    title: "NIRMIQ Runtime Status",
    message: apiOpen && webOpen ? "NIRMIQ local runtime is ready." : "NIRMIQ local runtime needs attention.",
    detail: [
      `API: ${apiOpen ? "online" : "offline"} (${API_URL})`,
      `Web: ${webOpen ? "online" : "offline"} (${WEB_URL})`,
      `Logs: ${TEMP_DIR}`,
      `Project: ${ROOT_DIR}`,
    ].join("\n"),
  });
}

function buildMenu() {
  return Menu.buildFromTemplate([
    {
      label: "NIRMIQ",
      submenu: [
        { label: "Reload Workspace", accelerator: "CmdOrCtrl+R", click: () => mainWindow?.reload() },
        { label: "Open DevTools", accelerator: "F12", click: () => mainWindow?.webContents.openDevTools() },
        { type: "separator" },
        { label: "Runtime Status", accelerator: "CmdOrCtrl+Shift+S", click: () => showRuntimeStatus() },
        { label: "Restart Local Runtime", click: () => restartRuntime().catch(showStartupError) },
        { label: "Open Project Folder", click: () => openPath(ROOT_DIR) },
        { label: "Open In VS Code", click: openInVsCode },
        { label: "Open context.md", click: () => openPath(path.join(ROOT_DIR, "context.md")) },
        { label: "Open README", click: () => openPath(path.join(ROOT_DIR, "README.md")) },
        { label: "Open Debugging Guide", click: () => openPath(path.join(ROOT_DIR, "debugging.md")) },
        { label: "Open Backend Architecture", click: () => openPath(path.join(ROOT_DIR, "backend_architecture.md")) },
        { label: "Open Data Folder", click: () => openPath(path.join(ROOT_DIR, "data")) },
        { type: "separator" },
        { role: "quit" },
      ],
    },
    {
      label: "Logs",
      submenu: [
        { label: "Open API Log", click: () => openPath(logPath("api")) },
        { label: "Open Web Log", click: () => openPath(logPath("web")) },
        { label: "Open Desktop Log Folder", click: () => openPath(TEMP_DIR) },
      ],
    },
    {
      label: "Edit",
      submenu: [
        { role: "undo" },
        { role: "redo" },
        { type: "separator" },
        { role: "cut" },
        { role: "copy" },
        { role: "paste" },
        { role: "selectAll" },
      ],
    },
  ]);
}

function showStartupError(error) {
  const message = error && error.message ? error.message : String(error);
  dialog.showErrorBox(
    "NIRMIQ startup failed",
    `${message}\n\nCheck logs in ${TEMP_DIR}. You can still run scripts/start_local.ps1 from PowerShell.`,
  );
}

ipcMain.handle("nirmiq:status", async () => ({
  apiUrl: API_URL,
  webUrl: WEB_URL,
  apiStartedByDesktop: Boolean(apiProcess),
  webStartedByDesktop: Boolean(webProcess),
  logDirectory: TEMP_DIR,
  rootDirectory: ROOT_DIR,
}));

ipcMain.handle("nirmiq:restart", async () => {
  await restartRuntime();
  return true;
});

app.whenReady().then(async () => {
  Menu.setApplicationMenu(buildMenu());
  try {
    await startRuntime();
    createMainWindow();
  } catch (error) {
    showStartupError(error);
    createMainWindow();
  }
});

app.on("before-quit", stopRuntime);

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("activate", () => {
  if (BrowserWindow.getAllWindows().length === 0) createMainWindow();
});
