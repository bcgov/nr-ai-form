import express from "express";
import { CosmosClient, Container } from "@azure/cosmos";
import { DefaultAzureCredential } from "@azure/identity";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const port = 3000;

// Use environment variables for Cosmos DB connection
// Log Cosmos DB configuration (excluding sensitive info)
// eslint-disable-next-line no-console
console.log("Configuring Cosmos DB client:", {
  endpoint: process.env.COSMOS_DB_ENDPOINT,
  databaseName: process.env.COSMOS_DB_DATABASE_NAME,
  containerName: process.env.COSMOS_DB_CONTAINER_NAME,
  authMethod: "Managed Identity",
});

let cosmosClient: CosmosClient;
let container: Container;

async function createCosmosClient() {
  try {
    // Check if we have an endpoint URL
    if (!process.env.COSMOS_DB_ENDPOINT) {
      throw new Error("COSMOS_DB_ENDPOINT environment variable is required");
    }

    if (!process.env.COSMOS_DB_DATABASE_NAME) {
      throw new Error(
        "COSMOS_DB_DATABASE_NAME environment variable is required"
      );
    }

    // Check if we're using the local emulator
    const isLocalEmulator =
      process.env.COSMOS_DB_ENDPOINT.includes("localhost") ||
      process.env.COSMOS_DB_ENDPOINT.includes("127.0.0.1");

    if (isLocalEmulator) {
      // Use the emulator key for local development
      cosmosClient = new CosmosClient({
        endpoint: process.env.COSMOS_DB_ENDPOINT,
        key: "C2y6yDjf5/R+ob0N8A7Cgv30VRDJIWEHLM+4QDU5DE2nQ9nDuVTqobD4b8mGGyPMbIZnqyMsEcaGQy67XIw/Jw==", // Default emulator key
      });
    } else {
      // Use Managed Identity for authentication when running in Azure
      // For local development, this will fall back to Azure CLI credentials
      const credential = new DefaultAzureCredential();

      cosmosClient = new CosmosClient({
        endpoint: process.env.COSMOS_DB_ENDPOINT,
        aadCredentials: credential,
      });
    }

    const database = cosmosClient.database(process.env.COSMOS_DB_DATABASE_NAME);
    container = database.container(
      process.env.COSMOS_DB_CONTAINER_NAME || "demo-container"
    );

    // Test the connection
    await database.read();

    // eslint-disable-next-line no-console
    console.log("Cosmos DB client created and connected successfully");
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error("Failed to create Cosmos DB client:", error);

    // Provide helpful error message for local development
    if (error instanceof Error && error.message.includes("credentials")) {
      // eslint-disable-next-line no-console
      console.error(
        "For local development, ensure you are logged in to Azure CLI: az login"
      );
    }

    throw error;
  }
}

const CONTAINER_NAME = process.env.COSMOS_DB_CONTAINER_NAME || "demo-container";
const DEMO_ITEM = {
  id: "1",
  message: "Hello from Cosmos DB!",
  partitionKey: "demo", // Cosmos DB requires a partition key
};

async function initDatabase() {
  try {
    // eslint-disable-next-line no-console
    console.log("Initializing Cosmos DB container and demo item...");

    // Create container if it doesn't exist
    const { container: containerResponse } = await cosmosClient
      .database(process.env.COSMOS_DB_DATABASE_NAME!)
      .containers.createIfNotExists({
        id: CONTAINER_NAME,
        partitionKey: "/partitionKey",
      });

    // Upsert demo item
    await container.items.upsert(DEMO_ITEM);

    // eslint-disable-next-line no-console
    console.log("Database initialization complete.");
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error("Database initialization failed:", error);
    throw error;
  }
}

import type { Request, Response } from "express";

app.get("/", async (_req: Request, res: Response) => {
  // eslint-disable-next-line no-console
  console.log("Received GET / request");
  try {
    // Query the demo item from Cosmos DB
    const { resource: item } = await container
      .item(DEMO_ITEM.id, DEMO_ITEM.partitionKey)
      .read();

    // eslint-disable-next-line no-console
    console.log("Cosmos DB query executed for demo item");

    if (item) {
      // eslint-disable-next-line no-console
      console.log("Item found, sending response:", item);
      res.json({ message: "Hello From CSS AI Team", ...item });
    } else {
      // eslint-disable-next-line no-console
      console.log("Item not found, sending 404");
      res.status(404).json({ error: "Item not found" });
    }
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("Cosmos DB error:", (err as Error).message);
    res
      .status(500)
      .json({ error: "Database error", details: (err as Error).message });
  }
});

// Health check endpoint
app.get("/health", async (_req: Request, res: Response) => {
  try {
    // Test Cosmos DB connection
    await cosmosClient.database(process.env.COSMOS_DB_DATABASE_NAME!).read();
    res.json({
      status: "healthy",
      database: "connected",
      timestamp: new Date().toISOString(),
    });
  } catch (error) {
    res.status(503).json({
      status: "unhealthy",
      database: "disconnected",
      error: (error as Error).message,
      timestamp: new Date().toISOString(),
    });
  }
});

app.listen(port, async () => {
  try {
    await createCosmosClient();
    await initDatabase();
    // eslint-disable-next-line no-console
    console.log(`API server running on port ${port}`);
  } catch (err) {
    // eslint-disable-next-line no-console
    console.error("Failed to initialize Cosmos DB:", err);
    process.exit(1);
  }
});
