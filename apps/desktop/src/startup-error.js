const title = document.querySelector("#failure-title");
const detail = document.querySelector("#failure-detail");
const action = document.querySelector("#failure-action");
const status = document.querySelector("#action-status");
const retryButton = document.querySelector("#retry");
const doctorButton = document.querySelector("#doctor");
const logsButton = document.querySelector("#logs");

async function loadFailure() {
  const failure = await window.nirmiqDesktop.getStartupFailure();
  if (!failure) return;
  title.textContent = failure.title;
  detail.textContent = failure.detail;
  action.textContent = failure.action;
}

async function runAction(button, pendingText, actionCall) {
  button.disabled = true;
  status.textContent = pendingText;
  try {
    const result = await actionCall();
    if (result?.ok === false) {
      status.textContent = result.failure?.action || "The local runtime still needs attention.";
      if (result.failure) {
        title.textContent = result.failure.title;
        detail.textContent = result.failure.detail;
        action.textContent = result.failure.action;
      }
    } else {
      status.textContent = "Action opened locally.";
    }
  } catch {
    status.textContent = "The action could not be completed. Open local logs for details.";
  } finally {
    button.disabled = false;
  }
}

retryButton.addEventListener("click", () =>
  runAction(retryButton, "Retrying the private local runtime...", () => window.nirmiqDesktop.retryStartup()),
);
doctorButton.addEventListener("click", () =>
  runAction(doctorButton, "Opening NIRMIQ Doctor...", () => window.nirmiqDesktop.runDoctor()),
);
logsButton.addEventListener("click", () =>
  runAction(logsButton, "Opening local logs...", () => window.nirmiqDesktop.openLogs()),
);

loadFailure().catch(() => {
  status.textContent = "Open local logs or run NIRMIQ Doctor to continue.";
});
