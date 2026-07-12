const { app, BrowserWindow, Menu, dialog, ipcMain, shell } = require("electron");
const fs = require("node:fs");
const http = require("node:http");
const net = require("node:net");
const path = require("node:path");
const { spawn } = require("node:child_process");

app.disableHardwareAcceleration();
app.commandLine.appendSwitch("in-process-gpu");
app.commandLine.appendSwitch("disable-gpu-sandbox");
app.commandLine.appendSwitch("disable-gpu-compositing");
app.commandLine.appendSwitch("disable-gpu-rasterization");
app.commandLine.appendSwitch("disable-accelerated-2d-canvas");
app.commandLine.appendSwitch("disable-features", "UseSkiaRenderer,Vulkan,CanvasOopRasterization");

function looksLikeProjectRoot(candidate) {
  if (!candidate) return false;
  return (
    fs.existsSync(path.join(candidate, "apps", "api", "app", "main.py")) &&
    fs.existsSync(path.join(candidate, "apps", "web", "package.json"))
  );
}

function walkUpForProjectRoot(startPath) {
  if (!startPath) return null;
  let current = path.resolve(startPath);
  for (let depth = 0; depth < 8; depth += 1) {
    if (looksLikeProjectRoot(current)) return current;
    const parent = path.dirname(current);
    if (parent === current) break;
    current = parent;
  }
  return null;
}

function resolveProjectRoot() {
  const candidates = [
    process.env.NIRMIQ_ROOT,
    process.env.PORTABLE_EXECUTABLE_DIR,
    process.env.PORTABLE_EXECUTABLE_FILE ? path.dirname(process.env.PORTABLE_EXECUTABLE_FILE) : null,
    path.resolve(__dirname, "..", "..", ".."),
    process.cwd(),
    process.resourcesPath,
    process.execPath ? path.dirname(process.execPath) : null,
  ];

  for (const candidate of candidates) {
    const root = walkUpForProjectRoot(candidate);
    if (root) return root;
  }

  return path.resolve(__dirname, "..", "..", "..");
}

const ROOT_DIR = resolveProjectRoot();
const API_DIR = path.join(ROOT_DIR, "apps", "api");
const WEB_DIR = path.join(ROOT_DIR, "apps", "web");
const TEMP_DIR = path.join(ROOT_DIR, "temp", "desktop");
const RUNTIME_DIR = path.join(ROOT_DIR, "temp", "runtime");
const API_URL = "http://127.0.0.1:8000";
const WEB_URL = "http://127.0.0.1:3002";
const API_HEALTH_URL = `${API_URL}/health`;
const USER_DATA_DIR = path.join(TEMP_DIR, "electron-user-data");

fs.mkdirSync(USER_DATA_DIR, { recursive: true });
app.setPath("userData", USER_DATA_DIR);

const isWindows = process.platform === "win32";
const npmCommand = isWindows ? "npm.cmd" : "npm";
const pythonCommand = isWindows ? "python" : "python3";

let mainWindow = null;
let apiProcess = null;
let webProcess = null;
let runtimeStarting = false;

function ensureRuntimeDir() {
  fs.mkdirSync(TEMP_DIR, { recursive: true });
  fs.mkdirSync(RUNTIME_DIR, { recursive: true });
}

function logPath(name) {
  ensureRuntimeDir();
  return path.join(TEMP_DIR, `${name}.log`);
}

function appendLog(name, line) {
  fs.appendFileSync(logPath(name), line);
}

function buildProcessEnv(extra = {}) {
  const env = {};
  const seen = new Set();

  for (const [key, value] of Object.entries(process.env)) {
    const normalized = isWindows ? key.toLowerCase() : key;
    if (normalized === "path") continue;
    if (isWindows && seen.has(normalized)) continue;
    seen.add(normalized);
    env[key] = value;
  }

  const pathValue = process.env.Path || process.env.PATH || "";
  if (isWindows) {
    env.Path = pathValue;
  } else {
    env.PATH = pathValue;
  }

  for (const [key, value] of Object.entries(extra)) {
    if ((isWindows ? key.toLowerCase() : key) === "path") {
      if (isWindows) {
        env.Path = value;
      } else {
        env.PATH = value;
      }
    } else {
      env[key] = value;
    }
  }

  return env;
}

function commandForPlatform(command, args) {
  if (!isWindows) {
    return { command, args };
  }

  return {
    command: "cmd.exe",
    args: ["/d", "/s", "/c", command, ...args],
  };
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

function waitForUrl(url, timeoutMs, child, label) {
  const startedAt = Date.now();
  return new Promise((resolve, reject) => {
    const attempt = () => {
      if (child?.spawnError) {
        reject(new Error(`${label || "Process"} failed to start: ${child.spawnError.message}`));
        return;
      }
      if (child?.exitInfo) {
        reject(new Error(`${label || "Process"} exited before ${url} was ready. Check ${logPath(label?.toLowerCase() || "runtime")}.`));
        return;
      }

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
  const platformCommand = commandForPlatform(command, args);
  appendLog(name, `\n\n[${new Date().toISOString()}] starting: ${platformCommand.command} ${platformCommand.args.join(" ")}\n`);
  appendLog(name, `[${new Date().toISOString()}] cwd: ${cwd}\n`);
  const child = spawn(platformCommand.command, platformCommand.args, {
    cwd,
    env: buildProcessEnv(env),
    windowsHide: true,
    shell: false,
  });
  child.stdout.on("data", (chunk) => appendLog(name, chunk.toString()));
  child.stderr.on("data", (chunk) => appendLog(name, chunk.toString()));
  if (child.pid) {
    fs.writeFileSync(path.join(TEMP_DIR, `${name}.pid`), String(child.pid));
    fs.writeFileSync(path.join(RUNTIME_DIR, `${name}.desktop.pid`), String(child.pid));
  }
  child.on("error", (error) => {
    child.spawnError = error;
    appendLog(name, `\n[${new Date().toISOString()}] spawn error: ${error.message}\n`);
  });
  child.on("exit", (code, signal) => {
    child.exitInfo = { code, signal };
    for (const pidPath of [path.join(TEMP_DIR, `${name}.pid`), path.join(RUNTIME_DIR, `${name}.desktop.pid`)]) {
      try {
        fs.rmSync(pidPath, { force: true });
      } catch {
        // Best-effort cleanup only.
      }
    }
    appendLog(name, `\n[${new Date().toISOString()}] exited code=${code} signal=${signal}\n`);
  });
  return child;
}

function stopChild(child) {
  if (!child || child.killed || !child.pid) return;
  if (isWindows) {
    spawn("taskkill", ["/pid", String(child.pid), "/t", "/f"], { windowsHide: true });
  } else {
    child.kill();
  }
}

async function startRuntime() {
  if (runtimeStarting) return;
  runtimeStarting = true;
  ensureRuntimeDir();
  let webScript = null;
  try {
    if (!(await isPortOpen(8000))) {
      apiProcess = spawnLoggedProcess(
        "api",
        pythonCommand,
        ["-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8000"],
        API_DIR,
        {
          PYTHONPATH: API_DIR,
        },
      );
    }

    if (!(await isPortOpen(3002))) {
      const hasBuild = fs.existsSync(path.join(WEB_DIR, ".next", "BUILD_ID"));
      webScript = hasBuild ? "start" : "dev";
      webProcess = spawnLoggedProcess("web", npmCommand, ["run", webScript], WEB_DIR, {
        NEXT_TELEMETRY_DISABLED: "1",
      });
    }

    await waitForUrl(API_HEALTH_URL, 60000, apiProcess, "api");
    try {
      await waitForUrl(WEB_URL, 60000, webProcess, "web");
    } catch (error) {
      if (webProcess && webScript === "start") {
        appendLog("web", `\n[${new Date().toISOString()}] production start failed, falling back to dev: ${error.message}\n`);
        stopChild(webProcess);
        webProcess = spawnLoggedProcess("web", npmCommand, ["run", "dev"], WEB_DIR, {
          NEXT_TELEMETRY_DISABLED: "1",
        });
        await waitForUrl(WEB_URL, 90000, webProcess, "web");
      } else {
        throw error;
      }
    }
  } finally {
    runtimeStarting = false;
  }
}

function stopRuntime() {
  for (const child of [webProcess, apiProcess]) {
    stopChild(child);
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
    title: "NIRMIQ Academic Intelligence",
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
