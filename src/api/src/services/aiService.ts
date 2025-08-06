import fetch from 'node-fetch';
const https = require('https');
import config from '../config/config';

export async function aiPrompt(prompt: string): Promise<any> {

  // Needed only for self-signed certs or local dev HTTPS, Don't use this in production
  const agent = new https.Agent({
    rejectUnauthorized: false
  });

  // Construct the URL from config values
  const url = `${config.aiBaseUrl}/openai/deployments/${config.aiDeployment}/chat/completions?api-version=${config.aiApiVersion}`;
  const body = JSON.stringify({
    messages: [{ role: 'system', content: prompt }],
    max_tokens: 50
  });

  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Host': config.aiHost,
      'api-key': config.aiKey,
      'Content-Type': 'application/json',
      'Content-Length': Buffer.byteLength(body).toString()
    },
    body: body,
    agent: agent // Use the custom agent to allow self-signed certs
  });
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
  }

  return response.json();

};

