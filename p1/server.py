# Central Index Server for P2P-CI
# Maintains active peers and RFC index, handles ADD/LOOKUP/LIST requests

import socket
import threading
from config import SERVER_PORT, VERSION
from protocol import parse_p2s_request, build_p2s_response, CRLF


class CentralServer:
    def __init__(self, host='0.0.0.0', port=SERVER_PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.lock = threading.Lock()
        self.peers = []       # [(hostname, port), ...]
        self.rfc_index = []   # [(rfc_number, title, hostname, port), ...]
        self.running = False
    
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.running = True
        
        print(f"[Server] Central Index Server started on port {self.port}")
        print(f"[Server] Waiting for peer connections...")
        
        try:
            while self.running:
                try:
                    client_socket, addr = self.server_socket.accept()
                    t = threading.Thread(target=self.handle_peer, args=(client_socket, addr))
                    t.daemon = True
                    t.start()
                except socket.error:
                    if self.running:
                        raise
        except KeyboardInterrupt:
            print("\n[Server] Shutting down...")
        finally:
            self.stop()
    
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[Server] Server stopped")
    
    def handle_peer(self, client_socket, client_addr):
        peer_host, peer_port = None, None
        first_msg = True
        
        try:
            while self.running:
                data = self.recv_message(client_socket)
                if not data:
                    break
                
                req = parse_p2s_request(data)
                if not req:
                    client_socket.send(build_p2s_response(400).encode())
                    continue
                
                if req['version'] != VERSION:
                    client_socket.send(build_p2s_response(505).encode())
                    continue
                
                peer_host = req['headers'].get('Host', client_addr[0])
                peer_port = int(req['headers'].get('Port', 0))
                
                if first_msg:
                    print(f"[Server] Connection from host {peer_host} at {client_addr[0]}:{peer_port}")
                    with self.lock:
                        if not self._peer_exists(peer_host, peer_port):
                            self.peers.insert(0, (peer_host, peer_port))
                            print(f"[Server] Added {peer_host}:{peer_port}")
                        self._print_state()
                    first_msg = False
                
                # Handle request
                method = req['method']
                if method == 'ADD':
                    response = self.handle_add(req, peer_host, peer_port)
                elif method == 'LOOKUP':
                    response = self.handle_lookup(req)
                elif method == 'LIST':
                    response = self.handle_list()
                else:
                    response = build_p2s_response(400)
                
                client_socket.send(response.encode())
                
        except Exception as e:
            print(f"[Server] Error handling peer {client_addr}: {e}")
        finally:
            if peer_host:
                self.remove_peer(peer_host, peer_port)
            client_socket.close()
            if peer_host and peer_port:
                print(f"[Server] Connection closed for {peer_host}:{peer_port}")
            else:
                print(f"[Server] Connection closed for {client_addr}")
    
    def recv_message(self, sock):
        data = b""
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    return None
                data += chunk
                if b"\r\n\r\n" in data:
                    break
            except socket.error:
                return None
        return data.decode()
    
    def _peer_exists(self, hostname, port):
        return any(h == hostname and p == port for h, p in self.peers)
    
    def _print_state(self):
        """Print server state (call with lock held)."""
        print("[Server] === Current State ===")
        if self.peers:
            print(f"[Server] Active Peers: {', '.join(f'{h}:{p}' for h, p in self.peers)}")
        else:
            print("[Server] Active Peers: (none)")
        
        if self.rfc_index:
            print("[Server] RFC Index:")
            for num, title, host, port in self.rfc_index:
                print(f"[Server]   RFC {num} {title} ({host}:{port})")
        else:
            print("[Server] RFC Index: (empty)")
        print("[Server] =========================")
    
    def handle_add(self, req, hostname, port):
        rfc_num = req['rfc_number']
        title = req['headers'].get('Title', '')
        
        with self.lock:
            if not self._peer_exists(hostname, port):
                self.peers.insert(0, (hostname, port))
                print(f"[Server] Added {hostname}:{port}")
            
            self.rfc_index.insert(0, (rfc_num, title, hostname, port))
            print(f"[Server] Added RFC {rfc_num} from {hostname}:{port}")
            self._print_state()
        
        return build_p2s_response(200, [f"RFC {rfc_num} {title} {hostname} {port}"])
    
    def handle_lookup(self, req):
        rfc_num = req['rfc_number']
        with self.lock:
            matches = [f"RFC {n} {t} {h} {p}" 
                      for n, t, h, p in self.rfc_index if n == rfc_num]
        
        if matches:
            return build_p2s_response(200, matches)
        return build_p2s_response(404)
    
    def handle_list(self):
        with self.lock:
            if not self.rfc_index:
                return build_p2s_response(404)
            lines = [f"RFC {n} {t} {h} {p}" for n, t, h, p in self.rfc_index]
        return build_p2s_response(200, lines)
    
    def remove_peer(self, hostname, port):
        with self.lock:
            self.peers = [(h, p) for h, p in self.peers 
                         if not (h == hostname and p == port)]
            self.rfc_index = [(n, t, h, p) for n, t, h, p in self.rfc_index 
                             if not (h == hostname and p == port)]
            print(f"[Server] Removed peer {hostname}:{port} and associated RFCs")
            self._print_state()


def main():
    print("=" * 50)
    print("P2P-CI Central Index Server")
    print("=" * 50)
    server = CentralServer()
    server.start()


if __name__ == "__main__":
    main()
