import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { execFileSync } from 'node:child_process';

// Sahne kodu HTML içinde; tek satırlık düzenlemelerde satır sonu yorumu kodu yutabiliyor. Sözdizimini denetle.
test('sahne betiği sözdizimi geçerli', () => {
  const html = readFileSync('public/index.html', 'utf8');
  const start = html.indexOf('<script type="module">') + '<script type="module">'.length;
  const js = html.slice(start, html.lastIndexOf('</script>'));
  const f = join(mkdtempSync(join(tmpdir(), 'bocek-')), 'sahne.mjs');
  writeFileSync(f, js);
  assert.doesNotThrow(() => execFileSync(process.execPath, ['--check', f], { stdio: 'pipe' }));
});
