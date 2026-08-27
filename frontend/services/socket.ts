export class SocketService {
  private socket: WebSocket | null = null;

  connect(url = "ws://localhost:8000/ws/live") {
    this.socket = new WebSocket(url);
    this.socket.addEventListener("open", () => {
      console.log("Live socket connected");
    });
    return this.socket;
  }

  disconnect() {
    this.socket?.close();
    this.socket = null;
  }
}

export const socketService = new SocketService();
