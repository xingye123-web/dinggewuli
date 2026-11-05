// 原型用的静态服务。拖动视频需要 Range 请求，所以不用最简单的静态服务器。
import { createReadStream, statSync } from 'node:fs'
import { createServer } from 'node:http'
import { extname, join, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = fileURLToPath(new URL('./', import.meta.url))
const port = Number(process.env.PORT || 4173)
const types = {
  '.html': 'text/html; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.mp4': 'video/mp4',
  '.js': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
}

createServer((req, res) => {
  const pathname = decodeURIComponent(new URL(req.url, 'http://x').pathname)
  const file = normalize(join(root, pathname === '/' ? 'player/index.html' : pathname))
  if (!file.startsWith(root)) {
    res.writeHead(403).end()
    return
  }

  let size
  try {
    size = statSync(file).size
  } catch {
    res.writeHead(404).end()
    return
  }

  const headers = { 'Content-Type': types[extname(file)] || 'application/octet-stream', 'Accept-Ranges': 'bytes' }
  const range = /bytes=(\d*)-(\d*)/.exec(req.headers.range || '')
  if (range) {
    const start = range[1] ? Number(range[1]) : 0
    const end = range[2] ? Number(range[2]) : size - 1
    res.writeHead(206, { ...headers, 'Content-Range': `bytes ${start}-${end}/${size}`, 'Content-Length': end - start + 1 })
    createReadStream(file, { start, end }).pipe(res)
    return
  }
  res.writeHead(200, { ...headers, 'Content-Length': size })
  createReadStream(file).pipe(res)
}).listen(port, () => console.log(`http://localhost:${port}`))
