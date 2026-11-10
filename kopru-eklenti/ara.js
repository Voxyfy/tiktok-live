// Eklenti dünyası: sayfadan gelen ham veriyi arka plana taşır (sayfanın CSP'si yerel sunucuya isteği engeller).
const toB64 = (buf) => {
  const bytes = new Uint8Array(buf); let s = '';
  for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(s);
};
window.addEventListener('message', (e) => {
  if (e.source !== window || !e.data?.__bocek) return;
  chrome.runtime.sendMessage({ kind: e.data.kind, b64: toB64(e.data.data) }).catch(() => {});
});
