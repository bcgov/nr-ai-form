import { copyFileSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const packageDir = fileURLToPath(new URL('./node_modules/promptfoo/', import.meta.url));
const bin = JSON.parse(readFileSync(join(packageDir, 'package.json'), 'utf8')).bin.promptfoo;
const directory = mkdtempSync(join(tmpdir(), 'nr-ai-form-eval-ci-'));
const report = join(directory, 'report.json');
let exitCode = 1;
try {
  const result = spawnSync(process.execPath, [
    join(packageDir, bin), 'eval', ...process.argv.slice(2), '--output', report,
  ], {
    stdio: 'inherit',
    env: { ...process.env, PROMPTFOO_PASS_RATE_THRESHOLD: '69' },
  });
  if (result.error) {
    throw result.error;
  }
  if (existsSync(report)) {
    const output = resolve('results');
    mkdirSync(output, { recursive: true });
    copyFileSync(report, join(output, 'latest.json'));
  }
  if (result.status === 0) {
    const rows = JSON.parse(readFileSync(report, 'utf8')).results?.results;
    if (!Array.isArray(rows) || rows.length === 0 || rows.some(row => typeof row.success !== 'boolean')) {
      throw new Error('Promptfoo returned an empty or invalid result set');
    }
    if (rows.some(row => row.response?.error || row.response?.output === undefined)) {
      throw new Error('Promptfoo contains provider/transport errors; this is not a valid quality run');
    }
    const passing = rows.filter(row => row.success).length;
    exitCode = passing * 100 >= rows.length * 69 ? 0 : 1;
  }
} finally {
  rmSync(directory, { recursive: true, force: true });
}
process.exit(exitCode);
