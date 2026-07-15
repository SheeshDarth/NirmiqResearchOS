const path = require("node:path");

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function redactDiagnosticText(value, sensitivePaths = []) {
  let text = String(value || "");
  for (const sensitivePath of sensitivePaths.filter(Boolean)) {
    const normalized = path.resolve(sensitivePath);
    const pathWithSuffix = `${escapeRegExp(normalized)}(?:[\\\\/][^\\r\\n\"'<>|]*)?`;
    text = text.replace(new RegExp(pathWithSuffix, "gi"), "<local-path>");
  }
  return text
    .replace(/[A-Za-z]:\\[^\r\n"'<>|]*/g, "<local-path>")
    .replace(/\s+at\s+file:\/\/\/[^\s)]+/gi, " at <local-file>");
}

function classifyStartupError(error) {
  const rawMessage = String(error?.message || error || "").toLowerCase();
  const code = String(error?.code || "").toUpperCase();

  if (code === "PROJECT_ROOT_MISSING") {
    return {
      kind: "project",
      title: "Local workspace not found",
      detail: "NIRMIQ could not locate the backend and web workspace required by this portable app.",
      action: "Keep the portable app inside the project folder, or set NIRMIQ_ROOT to that folder.",
    };
  }
  if (code === "ENOENT" || rawMessage.includes("failed to start")) {
    return {
      kind: "dependency",
      title: "A local runtime dependency is missing",
      detail: "Python, Node.js, npm, or an installed project dependency could not be started.",
      action: "Run NIRMIQ Doctor, then follow the single required action it reports.",
    };
  }
  if (rawMessage.includes("8000") || rawMessage.includes("api")) {
    return {
      kind: "api",
      title: "The local knowledge engine did not start",
      detail: "The private FastAPI service did not become healthy within the startup window.",
      action: "Run NIRMIQ Doctor. If it passes, open the local logs and retry.",
    };
  }
  if (rawMessage.includes("3002") || rawMessage.includes("web")) {
    return {
      kind: "web",
      title: "The local workspace did not start",
      detail: "The NIRMIQ interface did not become ready within the startup window.",
      action: "Run NIRMIQ Doctor. If it passes, rebuild the web app and retry.",
    };
  }
  return {
    kind: "runtime",
    title: "NIRMIQ could not finish local startup",
    detail: "The local runtime stopped before the academic workspace was ready.",
    action: "Run NIRMIQ Doctor, inspect the local logs if needed, and retry startup.",
  };
}

module.exports = {
  classifyStartupError,
  redactDiagnosticText,
};
