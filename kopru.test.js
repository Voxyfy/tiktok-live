import { test } from 'node:test';
import assert from 'node:assert/strict';
import { gzipSync } from 'node:zlib';
import { WebcastGiftMessage, WebcastChatMessage, WebcastLikeMessage, ProtoMessageFetchResult, BaseProtoMessage, User, Gift, CommonMessageData, createBaseWebcastPushFrame } from 'tiktok-live-connector';
import { decodeRaw } from './kopru.js';

// Eklentinin yakalayacağı ham çerçeveyi kütüphanenin kendi şemasıyla üret
// Şema kodlayıcısı her alanı ister: boş çözümden varsayılanları al, verilenleri üstüne yaz
const make = (T, o) => Object.assign(T.decode(new Uint8Array()), o);
const NESTED = { user: User, gift: Gift, common: CommonMessageData };
const full = (T, o) => make(T, Object.fromEntries(Object.entries(o).map(([k, v]) => [k, NESTED[k] ? make(NESTED[k], v) : v])));
const enc = (T, o) => T.encode(T === ProtoMessageFetchResult ? make(T, { messages: o.messages.map((m) => make(BaseProtoMessage, m)) }) : full(T, o)).finish();
function frameOf(messages, gzip = false) {
  let payload = enc(ProtoMessageFetchResult, { messages });
  if (gzip) payload = gzipSync(payload);
  const f = createBaseWebcastPushFrame({ payload: Buffer.from(payload), payloadType: 'msg' });
  return typeof f.finish === 'function' ? f.finish() : f;
}
const msg = (method, T, o) => ({ method, payload: enc(T, o) });

test('itme çerçevesinden hediye, yorum, beğeni çıkar; seri ortası atlanır', async () => {
  const buf = frameOf([
    msg('WebcastGiftMessage', WebcastGiftMessage, { common: { msgId: '11' }, user: { id: '9', nickname: 'Ayşe' }, gift: { name: 'Gül', diamondCount: 1, type: 1 }, repeatCount: 2, repeatEnd: 0 }),
    msg('WebcastGiftMessage', WebcastGiftMessage, { common: { msgId: '12' }, user: { id: '9', nickname: 'Ayşe' }, gift: { name: 'Gül', diamondCount: 1, type: 1 }, repeatCount: 3, repeatEnd: 1 }),
    msg('WebcastChatMessage', WebcastChatMessage, { common: { msgId: '13' }, user: { id: '7', nickname: 'Emre' }, content: 'halay başı kim' }),
    msg('WebcastLikeMessage', WebcastLikeMessage, { common: { msgId: '14' }, user: { id: '7', nickname: 'Emre' }, count: 15 }),
  ], true);
  const evs = await decodeRaw('frame', buf);
  assert.deepEqual(evs.map((e) => e.type), ['gift', 'chat', 'like']);
  assert.equal(evs[0].gift.count, 3); assert.equal(evs[0].gift.diamonds, 1); assert.equal(evs[0].user.name, 'Ayşe');
  assert.equal(evs[1].text, 'halay başı kim');
  assert.equal(evs[2].count, 15);
});

test('aynı mesaj ikinci kez gelirse sayılmaz (çekme + itme tekrarı)', async () => {
  const m = [msg('WebcastChatMessage', WebcastChatMessage, { common: { msgId: '99' }, user: { id: '1', nickname: 'X' }, content: 'selam' })];
  assert.equal((await decodeRaw('fetch', enc(ProtoMessageFetchResult, { messages: m }))).length, 1);
  assert.equal((await decodeRaw('frame', frameOf(m))).length, 0);
});
