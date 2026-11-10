// TikTok webcast verisini sahnenin tanıdığı sade olaylara çevirir.
// İki kaynak aynı çeviriyi kullanır:
//   - tiktok-live-connector olayları (--user modu, Euler imza sunucusu gerekir)
//   - tarayıcı eklentisinin yakaladığı ham çerçeveler (--tarayici modu, ücretsiz)
import { deserializeWebSocketMessage, deserializeMessage } from 'tiktok-live-connector';

export const who = (u) => ({ id: String(u?.id ?? u?.userId ?? ''), name: u?.nickname || u?.displayId || u?.uniqueId || 'Misafir' });

const img = (m) => m?.urlList?.[0] ?? m?.url_list?.[0] ?? null;

/** Tek bir çözülmüş webcast mesajını sahne olayına çevirir; ilgisizse null. */
export function toSceneEvent(type, d) {
  if (type === 'WebcastGiftMessage') {
    if (!d.gift) return null;
    // Seri hediyelerde repeatCount kümülatif; yalnız serinin son güncellemesi sayılır.
    if (d.gift.type === 1 && d.repeatEnd !== 1) return null;
    return { type: 'gift', user: who(d.user), gift: { name: d.gift.name, diamonds: d.gift.diamondCount ?? 0, count: d.repeatCount || 1, image: img(d.gift.image ?? d.gift.icon) } };
  }
  if (type === 'WebcastLikeMessage') return { type: 'like', user: who(d.user), count: d.count ?? d.likeCount ?? 1 };
  if (type === 'WebcastChatMessage') return { type: 'chat', user: who(d.user), text: d.content ?? d.comment ?? '' };
  return null;
}

// Aynı mesaj hem itme çerçevesinde hem yedek çekmede gelebilir; msgId ile tekilleştir.
const seen = new Set();
// Hata ayıklama: KOPRU_DEBUG=1 ile 15 sn'de bir gelen mesaj türlerini yaz
const debugCount = {};
if (process.env.KOPRU_DEBUG) setInterval(() => { console.log('[türler]', JSON.stringify(debugCount)); }, 15000).unref();
function fresh(d) {
  const id = d?.common?.msgId;
  if (!id || id === '0') return true;
  if (seen.has(id)) return false;
  seen.add(id); if (seen.size > 5000) seen.delete(seen.values().next().value);
  return true;
}

/**
 * Eklentiden gelen ham veriyi çöz.
 * kind 'frame': WebSocket itme çerçevesi (WebcastPushFrame, payload gzip olabilir)
 * kind 'fetch': HTTP yedek çekme yanıtı (doğrudan ProtoMessageFetchResult)
 */
export async function decodeRaw(kind, buf) {
  let result;
  if (kind === 'frame') {
    const frame = await deserializeWebSocketMessage(buf);
    if (process.env.KOPRU_DEBUG) { const k = `çerçeve:${frame.payloadType}/${frame.payloadEncoding}/${frame.protoMessageFetchResult ? 'çözüldü' : 'boş'}`; debugCount[k] = (debugCount[k] ?? 0) + 1; }
    // Yalnız kalp atışı/onay çerçevelerini atla; mesaj taşıyan her tür denenir
    if (frame.payloadType === 'hb' || frame.payloadType === 'ack') return [];
    result = frame.protoMessageFetchResult;
  } else {
    result = deserializeMessage('ProtoMessageFetchResult', Buffer.from(buf));
  }
  const out = [];
  if (process.env.KOPRU_DEBUG) for (const m of result?.messages ?? []) {
    const d = m.decodedData?.data;
    const k = m.method + (m.decodedData ? '' : m.decodeError ? ' (çözülemedi)' : ' (şema yok)') + (m.method === 'WebcastGiftMessage' && d ? ` [gift:${!!d.gift} tip:${d.gift?.type} son:${d.repeatEnd}]` : '');
    debugCount[k] = (debugCount[k] ?? 0) + 1;
  }
  for (const m of result?.messages ?? []) {
    if (!m.decodedData || !fresh(m.decodedData.data)) continue;
    const ev = toSceneEvent(m.decodedData.type, m.decodedData.data);
    if (ev) out.push(ev);
  }
  return out;
}
