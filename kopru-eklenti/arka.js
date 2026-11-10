// Arka plan: veriyi yerel Böcek Düğünü sunucusuna gönderir. Sunucu kapalıysa sessizce atlar.
chrome.runtime.onMessage.addListener((msg) => {
  fetch('http://localhost:3000/ham', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(msg) }).catch(() => {});
});
