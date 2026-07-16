const clientId = '11111111-1111-4111-8111-111111111111';
const API_BACKEND_BASE_URL = 'http://localhost:8003';
const WEBSOCKET_RESPONSE_TIMEOUT_MS = 180000;

function getApiBackendWebSocketUrl(session_id) {
  // Match the browser page protocol: http -> ws, https -> wss.
  const url = new URL('/ws', API_BACKEND_BASE_URL);
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
  if (session_id) {
    url.searchParams.set('session_id', session_id);
  }
  return url.toString();
}

async function invokeOrchestrator(query, step_number, session_id = null) {
  const socket = new WebSocket(getApiBackendWebSocketUrl(session_id));

  return new Promise((resolve, reject) => {
    const timeoutId = setTimeout(() => {
      socket.close();
      reject(new Error('Timed out waiting for API backend WebSocket response.'));
    }, WEBSOCKET_RESPONSE_TIMEOUT_MS);

    socket.onopen = () => {
      socket.send(JSON.stringify({
        client_id: clientId,
        query,
        step_number,
        session_id
      }));
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.event === 'session_init') return;
      clearTimeout(timeoutId);
      socket.close();
      if (data.error) {
        reject(new Error(String(data.error)));
        return;
      }
      resolve(data);
    };

    socket.onerror = () => {
      clearTimeout(timeoutId);
      reject(new Error('Unable to connect to API backend WebSocket.'));
    };

    socket.onclose = (event) => {
      if (event.wasClean) return;
      clearTimeout(timeoutId);
      reject(new Error(`API backend WebSocket closed: ${event.code || 'unknown'}`));
    };
  });
}

export { invokeOrchestrator };
