import fs from 'fs';
import { SourceMapConsumer } from 'source-map';

async function findNearest(mapPath, genLine, genColumn, window=1000) {
  const raw = await fs.promises.readFile(mapPath, 'utf8');
  const parsed = JSON.parse(raw);
  const consumer = await new SourceMapConsumer(parsed);
  try {
    const mappings = [];
    consumer.eachMapping(m => {
      if (m.generatedLine === Number(genLine)) {
        mappings.push(m);
      }
    });
    if (mappings.length === 0) {
      console.error('No mappings for generated line', genLine);
      return;
    }
    mappings.sort((a,b)=>a.generatedColumn-b.generatedColumn);
    // Find the mapping closest to genColumn that has an original source in src/
    let best = null;
    let bestDist = Infinity;
    for (const m of mappings) {
      if (!m.source) {
        continue;
      }
      if (!m.source.includes('/src/') && !m.source.includes('src/')) {
        continue;
      }
      const dist = Math.abs(m.generatedColumn - Number(genColumn));
      if (dist < bestDist) { bestDist = dist; best = m; }
    }
    if (best) {
      console.log(JSON.stringify({map:mapPath, gen:{line:genLine,column:genColumn}, found:best, nearestDistance:bestDist}, null, 2));
      return;
    }
    // If no src mapping in same line, expand search across other lines within +/- 2
    for (let d = 1; d <= 5; d++) {
      for (const offset of [ -d, d ]) {
        const targetLine = Number(genLine) + offset;
        for (const m of mappings.filter(mm => mm.generatedLine === targetLine || mm.generatedLine === Number(genLine))) {
          if (!m.source) {
            continue;
          }
          if (!m.source.includes('/src/') && !m.source.includes('src/')) {
            continue;
          }
          const dist = Math.abs((m.generatedLine - Number(genLine))*100000 + (m.generatedColumn - Number(genColumn)));
          if (dist < bestDist) { bestDist = dist; best = m; }
        }
        if (best) {
          break;
        }
      }
      if (best) {
        break;
      }
    }
    if (best) {
      console.log(JSON.stringify({map:mapPath, gen:{line:genLine,column:genColumn}, found:best, nearestDistance:bestDist}, null, 2));
    } else {
      console.log('No mapping to src/ found near generated position.');
    }
  } finally {
    consumer.destroy();
  }
}

if (process.argv.length < 5) {
  console.error('Usage: node find-nearest-src-mapping.mjs <map-file> <line> <column>');
  process.exit(2);
}
const [,, mapFile, line, column] = process.argv;
findNearest(mapFile, line, column).catch(err=>{console.error(err);process.exit(1)});
