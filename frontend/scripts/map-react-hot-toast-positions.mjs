import fs from 'fs';
import { SourceMapConsumer } from 'source-map';

const mapPath = './node_modules/.vite/deps/react-hot-toast.js.map';
if (!fs.existsSync(mapPath)) {
  console.error('Source map not found at', mapPath);
  process.exit(1);
}

const raw = JSON.parse(fs.readFileSync(mapPath, 'utf8'));

const positions = [
  { line: 53, column: 61 },
  { line: 54, column: 5 },
  { line: 66, column: 10 },
  { line: 233, column: 11 },
];

(async () => {
  await SourceMapConsumer.with(raw, null, consumer => {
    for (const pos of positions) {
      const orig = consumer.originalPositionFor({ line: pos.line, column: pos.column });
      console.log(`generated ${pos.line}:${pos.column} ->`, orig);
    }
  });
})();
