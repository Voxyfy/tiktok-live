// TikTok LIVE köprüsü: hediye/beğeni/yorum olaylarını sadeleştirip yerel WebSocket'e basar,
// aynı süreçte public/ klasörünü (OBS tarayıcı kaynağı) sunar.
//   node server.js --tarayici                   gerçek yayın, ÜCRETSİZ: Chrome eklentisi (kopru-eklenti/) yayın
//                                               sayfasındaki ham veriyi POST /ham ile buraya iletir
//   node server.js --user <tiktok_kullanici>   gerçek yayın, tiktok-live-connector (Euler imza sunucusu ücretli plan ister)
//   node server.js --fake                       sahte olay üreteci (yayın açmadan test)
import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, join } from 'node:path';
import { WebSocketServer } from 'ws';

const args = process.argv.slice(2);
const fake = args.includes('--fake');
const browser = args.includes('--tarayici');
const user = args.includes('--user') ? args[args.indexOf('--user') + 1] : null;
const port = Number(process.env.PORT ?? 3000);
if (!fake && !user && !browser) {
  console.error('Kullanım: node server.js --tarayici | --user <tiktok_kullanici> | --fake');
  process.exit(1);
}

const mime = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.css': 'text/css', '.mp3': 'audio/mpeg', '.glb': 'model/gltf-binary' };
const cache = new Map();
const server = http.createServer(async (req, res) => {
  if (req.method === 'POST' && req.url === '/ham') return receiveRaw(req, res);
  try {
    const p = decodeURIComponent(req.url.split('?')[0]);
    const path = p === '/' ? '/index.html' : p;   // ?sahne=bocek.app eki LIVE Studio'nun adres kontrolünü geçmek için
    if (path.includes('..')) throw new Error('yol dışı');
    // Büyük dosyalar (müzik, modeller) bir kez okunup bellekte tutulur: Safari müziği onlarca parça isteğiyle çeker
    // Dosya değiştiyse (ör. Blender yeniden üretti) önbellek tazelenir
    const file = join('public', path), mtime = (await stat(file)).mtimeMs;
    let body = cache.get(path)?.mtime === mtime ? cache.get(path).body : null;
    if (!body) { body = await readFile(file); if (/\.(mp3|glb)$/.test(path)) cache.set(path, { mtime, body }); }
    const type = mime[extname(path)] ?? 'application/octet-stream';
    // Müziğin döngüde başa sarabilmesi için tarayıcı parça (Range) ister.
    const m = /bytes=(\d*)-(\d*)/.exec(req.headers.range ?? '');
    if (m) {
      const start = Number(m[1] || 0), end = Math.min(body.length - 1, m[2] ? Number(m[2]) : body.length - 1);
      res.writeHead(206, { 'content-type': type, 'content-range': `bytes ${start}-${end}/${body.length}`, 'accept-ranges': 'bytes', 'content-length': end - start + 1 });
      return res.end(body.subarray(start, end + 1));
    }
    res.writeHead(200, { 'content-type': type, 'accept-ranges': 'bytes', 'content-length': body.length });
    res.end(body);
  } catch {
    res.writeHead(404); res.end();
  }
});
const wss = new WebSocketServer({ server });
// Odanın hediye kataloğu (ad, fiyat, ikon); yeni açılan sahneye hemen gönderilir.
let catalog = null;
wss.on('connection', (ws) => { if (catalog) ws.send(JSON.stringify({ type: 'catalog', gifts: catalog })); });
const broadcast = (ev) => {
  const msg = JSON.stringify(ev);
  for (const c of wss.clients) if (c.readyState === 1) c.send(msg);
};
server.listen(port, () => console.log(`Sahne: http://localhost:${port}  (${fake ? 'SAHTE olaylar' : browser ? 'tarayıcı eklentisi' : '@' + user})`));

// Sahnenin tanıdığı tek olay biçimi; TikTok verisi kopru.js'de sadeleşir.
const { who, toSceneEvent, decodeRaw } = await import('./kopru.js');

// Tarayıcı modu: eklenti {kind, b64} gönderir. Yalnız yerel istek kabul edilir; gövde 4 MB ile sınırlı.
let rawCount = 0, rawWindow = 0;
// Eklentiden veri akıyor mu? 30 sn'de bir paket sayısını yaz (yorum/hediye olmasa da akış görünür)
if (browser) setInterval(() => { console.log(`[eklenti] son 30 sn: ${rawWindow} paket`); rawWindow = 0; }, 30000).unref();
function receiveRaw(req, res) {
  const local = ['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(req.socket.remoteAddress);
  if (!browser || !local) { res.writeHead(403); return res.end(); }
  const chunks = []; let size = 0;
  req.on('data', (c) => { size += c.length; if (size > 4e6) req.destroy(); else chunks.push(c); });
  req.on('end', async () => {
    res.writeHead(204); res.end();
    try {
      const { kind, b64 } = JSON.parse(Buffer.concat(chunks).toString());
      const events = await decodeRaw(kind === 'fetch' ? 'fetch' : 'frame', Buffer.from(b64, 'base64'));
      rawWindow++;
      if (++rawCount === 1) console.log('Eklentiden ilk veri geldi, yayın okunuyor');
      for (const ev of events) {
        // Görülen hediyelerden katalog kur: menü gerçek hediye adı ve ikonuyla dolar
        if (ev.type === 'gift' && ev.gift.diamonds > 0 && !catalog?.some((g) => g.name === ev.gift.name)) {
          catalog = [...(catalog ?? []), { name: ev.gift.name, diamonds: ev.gift.diamonds, image: ev.gift.image }];
          broadcast({ type: 'catalog', gifts: catalog });
        }
        if (ev.type !== 'like') console.log(ev.type, ev.user.name, ev.type === 'gift' ? `${ev.gift.name} x${ev.gift.count} (${ev.gift.diamonds})` : ev.text);
        broadcast(ev);
      }
    } catch (err) { console.error('Ham veri çözülemedi:', err.message); }
  });
}

if (fake) {
  const names = ['Ahmet', 'Ayşe', 'Memik Can', 'Zeynep154', 'kurtbaş yusuf', 'Hatice', 'Emre', 'Aylin', 'Oğuz145', 'Seda'];
  const gifts = [['Gül', 1], ['Gül', 1], ['Gül', 1], ['Gül', 1], ['Gül', 1], ['Parmak Kalp', 5], ['Parmak Kalp', 5], ['Dondurma', 99], ['Taç', 299], ['Para Tabancası', 500], ['Uçak', 1200], ['Aslan', 2999], ['Evren', 44999]];
  const pick = (a) => a[Math.floor(Math.random() * a.length)];
  catalog = [...new Map(gifts.map(([name, diamonds]) => [name, { name, diamonds, image: null }])).values()];  // ikonsuz sahte katalog
  setInterval(() => {
    const n = pick(names); const u = { id: names.indexOf(n), nickname: n };
    const r = Math.random();
    if (r < 0.55) { const [name, diamonds] = pick(gifts); broadcast({ type: 'gift', user: who(u), gift: { name, diamonds, count: 1 } }); }
    else if (r < 0.85) broadcast({ type: 'like', user: who(u), count: 1 + Math.floor(Math.random() * 15) });
    else broadcast({ type: 'chat', user: who(u), text: pick(['kerizler toplanmış', 'halay başı kim', 'damat olcam', 'selam']) });
  }, 700);
} else if (user) {
  const { TikTokLiveConnection, WebcastEvent } = await import('tiktok-live-connector');
  const conn = new TikTokLiveConnection(user, { enableExtendedGiftInfo: true });
  for (const [ev, type] of [[WebcastEvent.GIFT, 'WebcastGiftMessage'], [WebcastEvent.LIKE, 'WebcastLikeMessage'], [WebcastEvent.CHAT, 'WebcastChatMessage']]) {
    conn.on(ev, (d) => { const e = toSceneEvent(type, d); if (e) broadcast(e); });
  }
  conn.on(WebcastEvent.DISCONNECTED, () => { console.log('Koptu, 5 sn sonra tekrar'); setTimeout(connect, 5000); });
  // Alan adları sürümden sürüme snake/camel değişebiliyor; ikisini de oku.
  const toCatalog = (g) => (Array.isArray(g) ? g : g?.gifts ?? g?.data?.gifts ?? []).map((x) => ({
    id: x.id, name: x.name, diamonds: x.diamond_count ?? x.diamondCount ?? 0,
    image: (x.image ?? x.icon)?.url_list?.[0] ?? (x.image ?? x.icon)?.urlList?.[0] ?? null,
  })).filter((x) => x.name && x.diamonds > 0);
  const connect = () => conn.connect().then((s) => {
    console.log('Bağlandı, oda', s.roomId);
    catalog = toCatalog(conn.availableGifts);
    console.log('Hediye kataloğu:', catalog.length, 'hediye');
    broadcast({ type: 'catalog', gifts: catalog });
  }).catch((err) => { console.error('Bağlanamadı:', err.message); setTimeout(connect, 10000); });
  connect();
}
