export function createFeedSocket(onMessage: (data: any) => void) {
  const socket = new WebSocket("ws://127.0.0.1:8000/ws/feed");

  socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };

  socket.onopen = () => {
    console.log("WS conectado");
  };

  socket.onclose = () => {
    console.log("WS desconectado");
  };

  return socket;
}