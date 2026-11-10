// Sayfa dünyasında çalışır: TikTok'un webcast bağlantısına gelen ham veriyi kopyalar.
// TikTok'un güvenlik kodu window.fetch / WebSocket'in orijinal olup olmadığını denetleyip sayfayı 403 ile
// engelleyebiliyor; bu yüzden ikisine de dokunulmaz. Yalnız MessageEvent.data okunduğunda, mesaj bir
// webcast WebSocket'inden geliyorsa kopyası alınır (her mesaj bir kez).
(() => {
  const desc = Object.getOwnPropertyDescriptor(MessageEvent.prototype, 'data');
  const seen = new WeakSet();
  const send = (buf) => window.postMessage({ __bocek: true, kind: 'frame', data: buf }, location.origin);
  Object.defineProperty(MessageEvent.prototype, 'data', {
    ...desc,
    get() {
      const v = desc.get.call(this);
      try {
        const src = this.target;
        if (!seen.has(this) && src instanceof WebSocket && /webcast/i.test(src.url)) {
          seen.add(this);
          if (v instanceof ArrayBuffer) send(v.slice(0));
          else if (v instanceof Blob) v.arrayBuffer().then(send);
        }
      } catch {}
      return v;
    },
  });
})();
