# nr-permitting-api

A simple TypeScript API that connects to Azure Cosmos DB at startup, creates a demo container and item, and exposes a GET endpoint to retrieve the item.

## Features

- **Azure Cosmos DB Integration**: Uses Azure Cosmos DB for NoSQL document storage
- **Managed Identity Authentication**: Securely authenticates with Cosmos DB using Azure Managed Identity
- **Express.js API**: RESTful API built with Express.js and TypeScript
- **Azure-Ready**: Configured for deployment to Azure App Service

## Development

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## Run

```bash
npm start
```

## Docker

```bash
docker build -t nr-permitting-api .
docker run --env-file .env -p 3000:3000 nr-permitting-api
```

## Environment Variables

- **COSMOS_DB_ENDPOINT**: The Cosmos DB account endpoint URL
- **COSMOS_DB_DATABASE_NAME**: The name of the Cosmos DB database
- **COSMOS_DB_CONTAINER_NAME**: The name of the container (defaults to 'demo-container')
- **PORT**: The port the server listens on (defaults to 3000)
- **NODE_ENV**: Environment mode (development/production)

## Authentication

The API uses Azure Managed Identity for authentication when deployed to Azure. For local development, ensure you're logged in to Azure CLI or provide appropriate credentials.

## API Endpoints

- `GET /`: Returns the demo item from Cosmos DB
