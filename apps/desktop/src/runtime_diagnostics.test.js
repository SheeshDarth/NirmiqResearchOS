const test = require("node:test");
const assert = require("node:assert/strict");
const { classifyStartupError, redactDiagnosticText } = require("./runtime_diagnostics");

test("classifies a missing project without returning a private path", () => {
  const error = new Error("Missing C:\\Users\\Student\\Private Notes\\apps\\api");
  error.code = "PROJECT_ROOT_MISSING";
  const result = classifyStartupError(error);

  assert.equal(result.kind, "project");
  assert.equal(JSON.stringify(result).includes("C:\\Users"), false);
});

test("classifies API readiness failures with an actionable local recovery", () => {
  const result = classifyStartupError(new Error("Timed out waiting for http://127.0.0.1:8000/health"));

  assert.equal(result.kind, "api");
  assert.match(result.action, /Doctor/);
});

test("redacts workspace and arbitrary Windows paths from diagnostics", () => {
  const result = redactDiagnosticText(
    "Failed at C:\\Nirmiq-researchOS\\apps\\api\nSource C:\\Users\\Student Name\\Private Notes\\notes.pdf",
    ["C:\\Nirmiq-researchOS", "C:\\Users\\Student Name"],
  );

  assert.equal(result.includes("Nirmiq-researchOS"), false);
  assert.equal(result.includes("Student"), false);
  assert.equal(result.includes("Private Notes"), false);
  assert.equal(result.includes("notes.pdf"), false);
  assert.match(result, /<local-path>/);
});
