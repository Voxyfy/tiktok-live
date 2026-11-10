// Halay adımı: 4 vuruşluk döngü, el ve ayak aynı vuruşa bağlı.
//   0: sağ ayak yana adım   1: sol ayak arkadan çapraz   2: sağ ayak yana adım   3: sol ayak öne tekme
// Kollar 0-2'de hafif geride, tekmede birlikte öne savrulur; omuzlar vuruşta silkinir.
// Açılar radyan; "R" böceğin sağı (sahnede -x), "L" solu. hipZ>0 bacağı sağa (-x) açar.
const smooth = (f) => f * f * (3 - 2 * f);

export function halayPose(beats) {
  const k = Math.floor(beats) % 4, f = beats - Math.floor(beats), bump = Math.sin(Math.PI * f);
  const R = { hipX: 0, hipZ: 0, knee: 0 }, L = { hipX: 0, hipZ: 0, knee: 0 };
  let arm = 0.15, bodyY = 0.05 * bump, tilt = 0;
  if (k === 0 || k === 2) { R.hipZ = 0.35 * bump; R.hipX = -0.25 * bump; R.knee = 0.7 * bump; tilt = 0.06 * bump; }
  else if (k === 1) { L.hipZ = 0.25 * bump; L.hipX = 0.3 * bump; L.knee = 0.8 * bump; tilt = -0.04 * bump; }
  else { L.hipX = -0.95 * bump; L.knee = 0.25 * bump; arm = 0.15 - 0.75 * bump; bodyY = 0.09 * bump; }
  // Yana kayma: üç adımda sağa, tekmede geri; döngü sonunda yerine döner (dikey çerçevede halay yerinde kalır).
  const shift = [[0, 0.12], [0.12, 0.18], [0.18, 0.3], [0.3, 0]][k];
  return { R, L, arm, bodyY, tilt, shrug: 0.04 * bump, shift: shift[0] + (shift[1] - shift[0]) * smooth(f) };
}

// Horon (Karadeniz): omuz omuza, dizler sürekli yaylanır, yerinde hızlı küçük adımlar, gövde titrer;
// her 8 vuruşta bir topluca çöküp kalkılır. halayPose ile aynı biçimi döndürür.
export function horonPose(beats) {
  const f = beats - Math.floor(beats), bump = Math.sin(Math.PI * f);
  const right = Math.floor(beats) % 2 === 0;          // ayaklar sırayla
  const bar = beats % 8, squat = bar >= 6 ? Math.sin(Math.PI * (bar - 6) / 2) : 0;   // 6-8. vuruşta çökme
  const lift = 0.35 * bump * (1 - squat);
  const R = { hipX: right ? -lift : 0, hipZ: 0, knee: 0.35 + (right ? 0.5 * bump : 0) + 0.9 * squat };
  const L = { hipX: right ? 0 : -lift, hipZ: 0, knee: 0.35 + (right ? 0 : 0.5 * bump) + 0.9 * squat };
  return {
    R, L,
    arm: 0.1 + Math.sin(beats * Math.PI * 2) * 0.12,        // kenetli kollar vuruşla aşağı yukarı titrer
    bodyY: -0.06 - 0.04 * bump - 0.28 * squat,              // dizler kırık: gövde hep biraz aşağıda
    tilt: Math.sin(beats * Math.PI * 4) * 0.035,            // hızlı omuz titremesi
    shrug: Math.abs(Math.sin(beats * Math.PI * 2)) * 0.05,
    shift: Math.sin(beats * Math.PI / 4) * 0.12,            // sıra yavaşça sağa sola salınır
  };
}
