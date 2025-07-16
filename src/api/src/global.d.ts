/* Global types for Node.js */
declare namespace NodeJS {
  interface ProcessEnv {
    DB_HOST: string;
    DB_PORT: string;
    DB_NAME: string;
    DB_USER: string;
    DB_PASSWORD: string;
    DB_SSL_MODE: string;
    DB_CONNECTION_TIMEOUT: string;
    DB_POOL_MIN: string;
    DB_POOL_MAX: string;
    NODE_ENV: string;
    PORT: string;
  }
}
