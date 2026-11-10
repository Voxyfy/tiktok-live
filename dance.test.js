import { test } from 'node:test';
import assert from 'node:assert/strict';
import { halayPose } from './public/dance.js';

test('aynı anda iki ayak birden kalkmaz', () => {
  for (let b = 0; b < 8; b += 0.05) {
    const p = halayPose(b);
    assert.ok(!(p.R.knee > 0.05 && p.L.knee > 0.05), `vuruş ${b.toFixed(2)}`);
  }
});

test('kollar yalnız tekme vuruşunda öne savrulur', () => {
  assert.ok(halayPose(3.5).arm < -0.5);
  for (const b of [0.5, 1.5, 2.5]) assert.equal(halayPose(b).arm, 0.15);
});

test('kayma sürekli ve döngü sonunda yerine döner', () => {
  for (let b = 0.01; b < 12; b += 0.01) assert.ok(Math.abs(halayPose(b).shift - halayPose(b - 0.01).shift) < 0.02, `vuruş ${b.toFixed(2)}`);
  assert.ok(Math.abs(halayPose(3.999).shift) < 0.01);
});

test('horon: ayaklar sırayla kalkar, çökmede iki diz birden bükülür', async () => {
  const { horonPose } = await import('./public/dance.js');
  for (let b = 0; b < 6; b += 0.05) { const p = horonPose(b); assert.ok(!(p.R.hipX < -0.05 && p.L.hipX < -0.05), `vuruş ${b.toFixed(2)}`); }
  const s = horonPose(7); assert.ok(s.R.knee > 1 && s.L.knee > 1 && s.bodyY < -0.25);
});
