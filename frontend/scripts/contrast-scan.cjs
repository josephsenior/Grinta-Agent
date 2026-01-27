const fs = require('fs');
const path = require('path');
const root = path.resolve(__dirname, '..');
const ignoreDirs = ['node_modules', 'dist', 'build', '.git'];
const hexRegex = /#([0-9A-Fa-f]{6})/g;

const hexToRgb = (h)=>{h=h.replace('#','');if (h.length===3) {
                                             h=h.split('').map(c=>c+c).join('');
                                           }return [parseInt(h.slice(0,2),16),parseInt(h.slice(2,4),16),parseInt(h.slice(4,6),16)];};
const lum=(hex)=>{const [r,g,b]=hexToRgb(hex).map(v=>v/255);const conv=c=>c<=0.03928?c/12.92:Math.pow((c+0.055)/1.055,2.4);const R=conv(r),G=conv(g),B=conv(b);return 0.2126*R+0.7152*G+0.0722*B;};
const contrast=(a,b)=>{const L1=lum(a);const L2=lum(b);const bright=Math.max(L1,L2),dim=Math.min(L1,L2);return (bright+0.05)/(dim+0.05);};

const backgrounds = [{name:'base',hex:'#0D0D0F'},{name:'base-secondary',hex:'#222328'}];

function walk(dir, cb){
  const entries = fs.readdirSync(dir, {withFileTypes:true});
  for(const e of entries){
    if (ignoreDirs.includes(e.name)) {
      continue;
    }
    const full = path.join(dir,e.name);
    if (e.isDirectory()) {
      walk(full, cb);
    } else {
      cb(full);
    }
  }
}

const occurrences = new Map();
walk(root, (file)=>{
  try{
    const rel = path.relative(root, file);
    // only scan frontend files (exclude large assets) - ensure within frontend
    if (!rel.startsWith('')) {
      return;
    } // keep
    if(!file.includes(path.join('Forge','frontend')) && !file.includes(path.join('frontend'))) {
      // skip files outside frontend
    }
    // skip binaries
    if (['.png','.jpg','.jpeg','.gif','.ico','.woff','.woff2','.ttf','.svg'].some(ext=>file.endsWith(ext))) {
      return;
    }
    const txt = fs.readFileSync(file,'utf8');
    let m; while((m=hexRegex.exec(txt))){
      const hex = '#'+m[1].toUpperCase();
      if (!occurrences.has(hex)) {
        occurrences.set(hex, {count:0,files:new Set()});
      }
      const info = occurrences.get(hex);
      info.count++;
      if (info.files.size<3) {
        info.files.add(rel);
      }
    }
  }catch(e){/* ignore */}
});

const results = [];
for(const [hex,info] of occurrences.entries()){
  const item = {hex, count:info.count, files:[...info.files].slice(0,3)};
  item.contrast = {};
  for(const bg of backgrounds){
    item.contrast[bg.name] = Number(contrast(hex,bg.hex).toFixed(2));
  }
  item.flag = Object.values(item.contrast).some(c=>c<4.5);
  results.push(item);
}

results.sort((a,b)=> (a.flag === b.flag ? b.count - a.count : (a.flag? -1:1)));

console.log('Found',results.length,'unique hex colors.\n');
console.log('Colors flagged (contrast <4.5 on any background) are listed first.\n');
for(const r of results){
  const flag = r.flag ? '⚠️' : '   ';
  console.log(`${flag} ${r.hex} — uses: ${r.count} — contrast: base=${r.contrast['base']}, base-secondary=${r.contrast['base-secondary']} \n    sample files: ${r.files.join(', ')}`);
}

// Write to JSON for further inspection
fs.writeFileSync(path.join(root,'contrast-scan-report.json'), JSON.stringify(results,null,2));
console.log('\nWrote report to frontend/contrast-scan-report.json');

const flagged = results.filter(r => r.flag);
if(flagged.length > 0){
  console.error(`\n${flagged.length} color(s) flagged: contrast < 4.5 on at least one background. Failing.`);
  // keep the report for inspection and exit non-zero so CI can fail
  process.exit(1);
} else {
  console.log('\nNo colors flagged. Contrast check passed.');
  process.exit(0);
}

