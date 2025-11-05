const fs = require('fs');
const path = require('path');

const buildDir = path.join(__dirname, '..', 'build');
const clientDir = path.join(buildDir, 'client');

if (!fs.existsSync(clientDir)) {
  console.log('No client directory to unpack');
  process.exit(0);
}

// Recursively copy all files from client to build
function copyRecursive(src, dest) {
  const entries = fs.readdirSync(src, { withFileTypes: true });
  
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    
    if (entry.isDirectory()) {
      // Create directory if it doesn't exist
      if (!fs.existsSync(destPath)) {
        fs.mkdirSync(destPath, { recursive: true });
      }
      // Recursively copy directory contents
      copyRecursive(srcPath, destPath);
    } else {
      // Copy file
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

try {
  copyRecursive(clientDir, buildDir);
  fs.rmSync(clientDir, { recursive: true, force: true });
  console.log('✓ Unpacked client directory');
} catch (err) {
  console.error('Failed to unpack client directory:', err);
  process.exit(1);
}

