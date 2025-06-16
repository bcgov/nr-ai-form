import express, { Request, Response } from "express";
import { errorHandler } from './middleware/errorHandler';
import config from './config/config';

import webformRoutes from "./routes/webform";

const app = express();

// ---- cors configuration
var cors = require('cors')
app.use(cors({
  origin: 'http://localhost:5173',
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
const wss = new WebSocket.Server({ port: 8080 });
wss.on('connection', (ws: any) => {
  console.log('A new client connected.');

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
