import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const root = path.resolve('web');
http.createServer((req,res) => {
 const p = new URL(req.url,'http://localhost').pathname;
 const file = path.resolve(root, '.' + decodeURIComponent(p === '/' ? '/index.html' : p));
 if (!file.startsWith(root + path.sep)) {res.writeHead(403).end();return;}
 fs.readFile(file,(error,data) => {if(error){res.writeHead(404).end('Not found');return;}
 res.setHeader('Content-Type',({'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8','svg':'image/svg+xml'})[path.extname(file).slice(1)] || 'application/octet-stream');
 res.setHeader('Cache-Control','no-store');res.end(data);});
}).listen(Number(process.env.PORT || 4173),'0.0.0.0',() => process.stdout.write('Sidra preview: http://localhost:4173/?demo=1\n'));
