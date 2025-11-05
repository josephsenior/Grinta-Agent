const fs = require("fs");
const path = require("path");

const reportPath = path.join(__dirname, "..", "eslint-report.json");
if (!fs.existsSync(reportPath)) {
  console.error("eslint-report.json not found at", reportPath);
  process.exit(2);
}
const raw = fs.readFileSync(reportPath, "utf8");
let data;
try {
  data = JSON.parse(raw);
} catch (e) {
  console.error("Failed to parse eslint-report.json:", e.message);
  process.exit(3);
}
const errors = data.filter((f) => f.errorCount > 0);
if (errors.length === 0) {
  console.log("No files with ESLint errors (errorCount>0)");
  process.exit(0);
}
errors.forEach((f) => {
  console.log("FILE:", f.filePath, "ERRORS:", f.errorCount);
  f.messages.forEach((m) => {
    if (m.severity === 2) {
      console.log(
        `  - [${m.ruleId}] line:${m.line} col:${m.column} ${m.message}`,
      );
    }
  });
});
console.log("\nSUMMARY: files with errors:", errors.length);
