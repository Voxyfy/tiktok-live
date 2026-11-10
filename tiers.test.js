import { test } from 'node:test';
import assert from 'node:assert/strict';
import { tierFor, TIERS } from './public/tiers.js';

test('eşik çözümü', () => {
  assert.equal(tierFor(0), null);
  assert.equal(tierFor(1).id, 'join');
  assert.equal(tierFor(98).id, 'join');
  assert.equal(tierFor(99).id, 'speed');
  assert.equal(tierFor(299).id, 'firework');
  assert.equal(tierFor(3600).id, 'basi');
  assert.equal(tierFor(99999).id, 'basi');
});

test('eşikler artan sırada', () => {
  for (let i = 1; i < TIERS.length; i++) assert.ok(TIERS[i].min > TIERS[i - 1].min);
});
