import express, { Request, Response } from "express";
import { errorHandler } from './middleware/errorHandler';
import config from './config/config';

import webformRoutes from "./routes/webform";

const app = express();

// ---- cors configuration
var cors = require('cors')
app.use(cors({
  origin: function (origin: string, callback: (err: Error | null, allow?: boolean) => void) {
    // Allow requests with no origin (like mobile apps, curl, Postman)
    if (!origin) return callback(null, true);
    
    // Define allowed origins
    const allowedOrigins = [
      'http://localhost:5173',
      'http://localhost:5174',
      'http://localhost:3000',
      'https://jatindersingh93.github.io',
      'https://cdn.jsdelivr.net'
    ];
    
    if (allowedOrigins.indexOf(origin) !== -1 || !origin) {
      callback(null, true);
    } else {
      callback(new Error('Not allowed by CORS'));
    }
  },
  methods: 'GET,HEAD,PUT,PATCH,POST,DELETE',
  credentials: true, // Allow cookies to be sent with requests
  optionsSuccessStatus: 200
}))


// ---- http connections
app.get("/", (req: Request, res: Response) => {
  res.send("base route");
});
// api routes
app.use("/api", webformRoutes);


app.use(errorHandler);

// start the server
app.listen(config.port, () => {
  console.log(`Server is running on port ${config.port}`);
});

// ---- WebSocket connections
const WebSocket = require('ws');
const http = require('http');

// Create a server instance for WebSocket to use
const wsServer = http.createServer();

// Set up WebSocket server with proper CORS headers
const wss = new WebSocket.Server({ 
  server: wsServer,
  // Handle WebSocket-specific CORS validation
  verifyClient: (info: { origin: string }) => {
    const allowedOrigins = [
      'http://localhost:5173',
      'http://localhost:5174',
      'http://localhost:3000',
      'https://jatindersingh93.github.io'
    ];
    
    const origin = info.origin || '';
    return allowedOrigins.indexOf(origin) !== -1 || !origin;
  }
});

// Start WebSocket server on port 8081
wsServer.listen(8082, () => {
  console.log('WebSocket server is running on port 8082');
});

wss.on('connection', (ws: any, req: any) => {
  console.log('A new client connected from:', req.socket.remoteAddress);

  ws.on('message', (message: any) => {
    console.log('Received message:', message);

    // reply to client (for demo, with same data)
    ws.send(message.toString());

    // Broadcast the message to all connected clients
    // wss.clients.forEach((client:any) => {
    //   if (client.readyState === WebSocket.OPEN) {

    //     // TODO: fetch ai data
    //     if(message.formId) {

    //       // const ai = 
    //       client.send( message.toString());
    //     }
    //   }
    // });
  });

  ws.on('close', () => {
    console.log('A client disconnected.');
  });
});
