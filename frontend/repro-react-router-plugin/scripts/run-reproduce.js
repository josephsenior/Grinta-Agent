const { spawn } = require("child_process");
const fs = require("fs");

const out = fs.createWriteStream("reproduce.log", { flags: "w" });

const child = spawn("npx", ["react-router", "dev"], { shell: true });

child.stdout.on("data", (d) => {
  out.write(d);
  process.stdout.write(d);
});
child.stderr.on("data", (d) => {
  out.write(d);
  process.stderr.write(d);
});
child.on("close", (code) => {
  out.write(`\nProcess exited with code ${code}\n`);
  out.end();
  console.log(`reproduce: finished with code ${code}`);
  process.exit(code);
});
