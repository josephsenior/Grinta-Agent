const sirv = require('sirv');
const http = require('http');
const path = require('path');
const finalhandler = require('finalhandler');
const serveStatic = require('serve-static');
const port = 3002;
const buildDir = path.resolve(__dirname, 'build');
console.log('serving', buildDir);
const serve = serveStatic(buildDir, { index: ['index.html'] });
const server = http.createServer((req, res) => {
  serve(req, res, finalhandler(req, res));
});
server.listen(port, () => {
  console.log('server listening on', port);
});

process.on('SIGTERM', () => server.close());
process.on('SIGINT', () => server.close());
