// The pinned Promptfoo version renders provider IDs, but not apiHost/apiVersion.
const apiHost = process.env.AZURE_OPENAI_ENDPOINT_HOST;
if (!apiHost) {
  throw new Error('AZURE_OPENAI_ENDPOINT_HOST must be configured in evaluation/.env');
}

module.exports = {
  description: 'nr-ai-form water permit assistant - per-step golden evaluation',
  providers: [{ id: 'file://providers/backend_provider.py', label: 'orchestrator-gpt51' }],
  prompts: ['{{query}}'],
  defaultTest: {
    options: {
      provider: {
        id: `azureopenai:chat:${process.env.FOUNDRY_MODEL || 'gpt-5.1'}`,
        config: {
          apiHost,
          apiVersion: process.env.AZURE_OPENAI_API_VERSION || '2025-04-01-preview',
          // Match the Python judge's messages-only request instead of legacy sampling/token defaults.
          passthrough: {
            max_tokens: undefined,
            temperature: undefined,
            top_p: undefined,
            presence_penalty: undefined,
            frequency_penalty: undefined,
          },
        },
      },
    },
    assert: [
      { type: 'not-empty' },
      {
        type: 'llm-rubric',
        value: 'The response must not fabricate specific dollar fees, water rates, legal ' +
          'citations, or eligibility rules that are not part of BC water licensing policy. ' +
          'If it is unsure it should say so or point to an authoritative BC source.',
      },
    ],
  },
  tests: 'file://../datasets/golden_tests.yaml',
  outputPath: 'results/latest.json',
};
