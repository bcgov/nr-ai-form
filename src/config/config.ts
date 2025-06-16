// loads your environment variables from a .env file and provides type checking.
import dotenv from 'dotenv';

dotenv.config();

interface Config {
  port: number;
  nodeEnv: string;
  aiKey: string;
}

const config: Config = {
  port: Number(process.env.PORT) || 3000,
  nodeEnv: process.env.NODE_ENV || 'development',
  aiKey: String(process.env.AI_KEY) || '',
};

export default config;
