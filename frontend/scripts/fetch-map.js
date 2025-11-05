import fs from "fs";

const url =
  "http://localhost:3002/node_modules/.vite/deps/react-hot-toast.js.map";
const outPath = "./node_modules/.vite/deps/react-hot-toast.js.map";

async function fetchToFile(url, dest) {
  const res = await fetch(url);
  if (!res.ok) {
    console.error("Failed to fetch map:", res.status, res.statusText);
    process.exit(1);
  }
  const buf = Buffer.from(await res.arrayBuffer());
  await fs.promises.mkdir("./node_modules/.vite/deps", { recursive: true });
  await fs.promises.writeFile(dest, buf);
  console.log("Wrote", dest);
}

fetchToFile(url, outPath).catch((err) => {
  console.error("Request failed", err && err.message ? err.message : err);
  process.exit(1);
});
