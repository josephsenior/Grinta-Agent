const http = require('http');
const path = require('path');
const finalhandler = require('finalhandler');
const serveStatic = require('serve-static');

const port = 3001;
const host = '127.0.0.1';
const buildDir = path.resolve(__dirname, '..', 'build');

console.log('serving', buildDir, 'on', host + ':' + port);
const serve = serveStatic(buildDir, { index: ['index.html'] });
const server = http.createServer((req, res) => {
  serve(req, res, finalhandler(req, res));
});
server.listen(port, host, () => {
  console.log('server listening on', host + ':' + port);
});

process.on('SIGTERM', () => server.close());
process.on('SIGINT', () => server.close());
