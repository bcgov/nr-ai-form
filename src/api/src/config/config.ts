// loads your environment variables from a .env file and provides type checking.
import dotenv from 'dotenv';

dotenv.config();

interface Config {
  port: number;
  nodeEnv: string;
  aiKey: string;
  aiBaseUrl: string;
  aiHost: string;
  aiDeployment: string;
  aiApiVersion: string;
}

const config: Config = {
  port: Number(process.env.PORT) || 3000,
  nodeEnv: process.env.NODE_ENV || 'development',
  aiKey: String(process.env.AI_KEY) || '',
  aiBaseUrl: process.env.AI_BASE_URL || 'https://127.0.0.1:8087',
  aiHost: process.env.AI_HOST || 'css-ai-dev-openai-east.openai.azure.com',
  aiDeployment: process.env.AI_DEPLOYMENT || 'gpt-4o-mini',
  aiApiVersion: process.env.AI_API_VERSION || '2025-01-01-preview',
};


export default config;
