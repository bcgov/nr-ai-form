import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';
import { test } from 'node:test';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(join(root, 'package.json'), 'utf8'));
assert.match(manifest.scripts['eval:ci'], /^node eval-ci\.mjs /);
const require = createRequire(import.meta.url);

test('judge deployment, host and API version resolve without literal placeholders', async () => {
  const values = {
    FOUNDRY_MODEL: 'offline-model',
    AZURE_OPENAI_ENDPOINT_HOST: 'model.invalid',
    AZURE_OPENAI_API_VERSION: '2025-04-01-preview',
  };
  const original = Object.fromEntries(Object.keys(values).map(key => [key, process.env[key]]));
  try {
    Object.assign(process.env, values);
    const golden = require(join(root, 'promptfooconfig.js'));
    const redteam = require(join(root, 'redteam.js'));
    const judge = golden.defaultTest.options.provider;
    assert.deepEqual(redteam.redteam.provider, judge);
    const { loadApiProvider } = require(join(root, 'node_modules', 'promptfoo', 'dist', 'src', 'providers'));
    const provider = await loadApiProvider(judge.id, {
      options: { config: { ...judge.config, apiKey: 'offline-test-key' } },
    });
    assert.equal(provider.deploymentName, 'offline-model');
    assert.equal(provider.getApiBaseUrl(), 'https://model.invalid');
    assert.equal(provider.config.apiVersion, values.AZURE_OPENAI_API_VERSION);
    const body = JSON.parse(JSON.stringify(provider.getOpenAiBody('question').body));
    assert.deepEqual(Object.keys(body).sort(), ['messages', 'model']);
  } finally {
    for (const [key, value] of Object.entries(original)) {
      if (value === undefined) {
        delete process.env[key];
      } else {
        process.env[key] = value;
      }
    }
  }
});

for (const [passing, expectedSuccess, transportError] of [[68, false, false], [69, true, false], [99, false, true]]) {
  test(`CI gate at ${passing}%${transportError ? ' with a provider error' : ''}`, () => {
    const directory = mkdtempSync(join(tmpdir(), 'nr-ai-form-threshold-'));
    try {
      const config = join(directory, 'config.json');
      if (transportError) {
        writeFileSync(join(directory, 'provider.js'), `
          module.exports = class {
            id() { return 'offline-provider'; }
            async callApi(prompt) {
              return prompt === 'answer-99'
                ? { error: 'synthetic transport failure' } : { output: prompt };
            }
          };
        `);
      }
      writeFileSync(config, JSON.stringify({
        providers: [transportError ? 'file://provider.js' : 'echo'],
        prompts: ['{{query}}'],
        tests: Array.from({ length: 100 }, (_, index) => ({
          vars: { query: `answer-${index}` },
          assert: [{ type: 'equals', value: index < passing ? `answer-${index}` : 'different' }],
        })),
      }));
      const result = spawnSync(process.execPath, [
        join(root, 'eval-ci.mjs'), '-c', config, '--no-cache', '--no-write',
      ], {
        cwd: directory,
        encoding: 'utf8',
        timeout: 60000,
        env: {
          ...process.env,
          PROMPTFOO_DISABLE_TELEMETRY: '1',
          PROMPTFOO_DISABLE_UPDATE: '1',
          PROMPTFOO_CONFIG_DIR: directory,
        },
      });
      assert.equal(result.error, undefined);
      assert.equal(result.status === 0, expectedSuccess, result.stdout + result.stderr);
      if (transportError) {
        assert.match(result.stderr, /provider\/transport errors/);
      } else {
        const report = JSON.parse(readFileSync(join(directory, 'results', 'latest.json'), 'utf8'));
        assert.equal(report.results.results.filter(row => row.success).length, passing);
      }
    } finally {
      rmSync(directory, { recursive: true, force: true });
    }
  });
}
