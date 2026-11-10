// Hediye eşikleri (elmas). Tek bir hediye olayının toplam elması hangi role denk geliyor?
// Yayıncı fiyatları burada değiştirir; sahne ve sağ menü bu listeden okunur.
export const TIERS = [
  { id: 'join',     min: 1,    label: 'Horona katıl' },
  { id: 'speed',    min: 99,   label: 'Hızlandır' },
  { id: 'firework', min: 299,  label: 'Havai fişek at' },
  { id: 'davulcu',  min: 500,  label: 'Davulcu ol' },
  { id: 'gelin',    min: 1200, label: 'Gelin ol' },
  { id: 'damat',    min: 2999, label: 'Damat ol' },
  { id: 'basi',     min: 3600, label: 'Horon başı ol' },
];

// Beğeni ile ücretsiz katılım eşiği (aynı kişinin birikmiş beğenisi).
export const LIKES_TO_JOIN = 100;

export function tierFor(diamonds) {
  let hit = null;
  for (const t of TIERS) if (diamonds >= t.min) hit = t;
  return hit;
}
