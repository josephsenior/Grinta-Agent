import fs from 'fs';
import path from 'path';
import { SourceMapConsumer } from 'source-map';

async function resolve(mapPath, line, column) {
  const raw = await fs.promises.readFile(mapPath, 'utf8');
  const parsed = JSON.parse(raw);
  const consumer = await new SourceMapConsumer(parsed);
  try {
    const pos = consumer.originalPositionFor({ line: Number(line), column: Number(column) });
    console.log(JSON.stringify({ map: mapPath, query: { line, column }, original: pos }, null, 2));
  } finally {
    consumer.destroy();
  }
}

if (process.argv.length < 5) {
  console.error('Usage: node resolve-sourcemap-frame.mjs <map-file> <line> <column>');
  process.exit(2);
}

const [,, mapFile, line, column] = process.argv;
resolve(mapFile, line, column).catch(err => { console.error(err); process.exit(1); });
