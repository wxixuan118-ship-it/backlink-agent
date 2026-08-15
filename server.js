const http = require('http');
const fs   = require('fs');
const path = require('path');

const PORT    = process.env.PORT || 3000;
const WEB_DIR = path.join(__dirname, 'web');

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.css':  'text/css',
  '.js':   'application/javascript',
  '.json': 'application/json',
  '.ico':  'image/x-icon',
  '.png':  'image/png',
  '.svg':  'image/svg+xml',
};

http.createServer((req, res) => {
  // Resolve path, default to index.html (SPA fallback)
  let rel = req.url.split('?')[0];
  let filePath = path.join(WEB_DIR, rel);

  // Security: stay inside web/
  if (!filePath.startsWith(WEB_DIR)) {
    res.writeHead(403); res.end('Forbidden'); return;
  }

  // If path doesn't exist or is a directory, serve index.html
  if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
    filePath = path.join(WEB_DIR, 'index.html');
  }

  const ext  = path.extname(filePath).toLowerCase();
  const mime = MIME[ext] || 'application/octet-stream';

  res.writeHead(200, { 'Content-Type': mime });
  fs.createReadStream(filePath).pipe(res);

}).listen(PORT, () => console.log(`Backlink Agent UI running on port ${PORT}`));
