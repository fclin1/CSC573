"""
Central Index Server for P2P-CI system.

Listens on port 7734 and maintains:
- List of active peers (hostname, upload_port)
- Index of RFCs (rfc_number, title, hostname)

Handles ADD, LOOKUP, LIST requests from peers.
"""

import socket
import threading
from config import SERVER_PORT, VERSION
from protocol import parse_p2s_request, build_p2s_response, CRLF


class CentralServer:
    def __init__(self, host='0.0.0.0', port=SERVER_PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        
        # Thread-safe data structures
        self.lock = threading.Lock()
        self.peers = []  # List of (hostname, port)
        self.rfc_index = []  # List of (rfc_number, title, hostname, port)
        
        self.running = False
    
    def start(self):
        """Start the server and listen for connections."""
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
                    client_socket, client_address = self.server_socket.accept()
                    
                    # Spawn a new thread for each peer
                    client_thread = threading.Thread(
                        target=self.handle_peer,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.error:
                    if self.running:
                        raise
        except KeyboardInterrupt:
            print("\n[Server] Shutting down...")
        finally:
            self.stop()
    
    def stop(self):
        """Stop the server."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
        print("[Server] Server stopped")
    
    def handle_peer(self, client_socket, client_address):
        """Handle communication with a connected peer."""
        peer_hostname = None
        peer_port = None
        first_message = True
        
        try:
            while self.running:
                # Receive data from peer
                data = self.receive_message(client_socket)
                if not data:
                    break
                
                # Parse the request
                request = parse_p2s_request(data)
                if not request:
                    response = build_p2s_response(400)
                    client_socket.send(response.encode('utf-8'))
                    continue
                
                # Check version
                if request['version'] != VERSION:
                    response = build_p2s_response(505)
                    client_socket.send(response.encode('utf-8'))
                    continue
                
                # Extract peer info from headers
                headers = request['headers']
                peer_hostname = headers.get('Host', client_address[0])
                peer_port = int(headers.get('Port', 0))
                
                # Log connection and show state on first message
                if first_message:
                    print(f"[Server] Connection from host {peer_hostname} at {client_address[0]}:{peer_port}")
                    # Add peer to list
                    with self.lock:
                        peer_exists = any(p[0] == peer_hostname and p[1] == peer_port for p in self.peers)
                        if not peer_exists:
                            self.peers.insert(0, (peer_hostname, peer_port))
                            print(f"[Server] Added {peer_hostname}:{peer_port}")
                        # Always show state when a new client connects
                        self.print_state_unlocked()
                    first_message = False
                
                # Handle the request
                method = request['method']
                if method == 'ADD':
                    response = self.handle_add(request, peer_hostname, peer_port)
                elif method == 'LOOKUP':
                    response = self.handle_lookup(request)
                elif method == 'LIST':
                    response = self.handle_list()
                else:
                    response = build_p2s_response(400)
                
                client_socket.send(response.encode('utf-8'))
                
        except Exception as e:
            print(f"[Server] Error handling peer {client_address}: {e}")
        finally:
            # Clean up peer data when connection closes
            if peer_hostname:
                self.remove_peer(peer_hostname, peer_port)
            client_socket.close()
            if peer_hostname and peer_port:
                print(f"[Server] Connection closed for {peer_hostname}:{peer_port}")
            else:
                print(f"[Server] Connection closed for {client_address}")
    
    def receive_message(self, sock):
        """Receive a complete message from socket."""
        data = b""
        while True:
            try:
                chunk = sock.recv(4096)
                if not chunk:
                    return None
                data += chunk
                # Check for end of message (double CRLF)
                if b"\r\n\r\n" in data:
                    break
            except socket.error:
                return None
        return data.decode('utf-8')
    
    def print_state_unlocked(self):
        """Print current server state (must be called with lock held)."""
        print("[Server] === Current State ===", flush=True)
        
        # Print active peers
        if self.peers:
            peer_list = ", ".join(f"{h}:{p}" for h, p in self.peers)
            print(f"[Server] Active Peers: {peer_list}", flush=True)
        else:
            print("[Server] Active Peers: (none)", flush=True)
        
        # Print RFC index
        if self.rfc_index:
            print("[Server] RFC Index:", flush=True)
            for rfc_num, title, hostname, port in self.rfc_index:
                print(f"[Server]   RFC {rfc_num} {title} ({hostname}:{port})", flush=True)
        else:
            print("[Server] RFC Index: (empty)", flush=True)
        
        print("[Server] =========================", flush=True)
    
    def print_state(self):
        """Print current server state (peers and RFC index)."""
        with self.lock:
            self.print_state_unlocked()
    
    def handle_add(self, request, hostname, port):
        """Handle ADD request - add RFC to index."""
        rfc_number = request['rfc_number']
        title = request['headers'].get('Title', '')
        
        with self.lock:
            # Ensure peer is in list (may already be added on first connection)
            peer_exists = any(p[0] == hostname and p[1] == port for p in self.peers)
            if not peer_exists:
                self.peers.insert(0, (hostname, port))
                print(f"[Server] Added {hostname}:{port}")
            
            # Add RFC to index (at front of list) - include port to distinguish peers
            self.rfc_index.insert(0, (rfc_number, title, hostname, port))
            print(f"[Server] Added RFC {rfc_number} from {hostname}:{port}")
            
            # Print current state after adding RFC
            self.print_state_unlocked()
        
        # Response echoes back the RFC info
        data_line = f"RFC {rfc_number} {title} {hostname} {port}"
        return build_p2s_response(200, [data_line])
    
    def handle_lookup(self, request):
        """Handle LOOKUP request - find peers with specified RFC."""
        rfc_number = request['rfc_number']
        
        with self.lock:
            # Find all records for this RFC
            matches = []
            for rfc_num, title, hostname, port in self.rfc_index:
                if rfc_num == rfc_number:
                    matches.append(f"RFC {rfc_num} {title} {hostname} {port}")
        
        if matches:
            return build_p2s_response(200, matches)
        else:
            return build_p2s_response(404)
    
    def handle_list(self):
        """Handle LIST request - return entire RFC index."""
        with self.lock:
            if not self.rfc_index:
                return build_p2s_response(404)
            
            data_lines = []
            for rfc_num, title, hostname, port in self.rfc_index:
                data_lines.append(f"RFC {rfc_num} {title} {hostname} {port}")
        
        return build_p2s_response(200, data_lines)
    
    def remove_peer(self, hostname, port):
        """Remove all records associated with a peer."""
        with self.lock:
            # Remove from peer list
            self.peers = [(h, p) for h, p in self.peers 
                         if not (h == hostname and p == port)]
            
            # Remove from RFC index (match both hostname and port)
            self.rfc_index = [(n, t, h, p) for n, t, h, p in self.rfc_index 
                             if not (h == hostname and p == port)]
            
            print(f"[Server] Removed peer {hostname}:{port} and associated RFCs")
            
            # Print current state after removal
            self.print_state_unlocked()


def main():
    """Main entry point for the server."""
    print("=" * 50)
    print("P2P-CI Central Index Server")
    print("=" * 50)
    
    server = CentralServer()
    server.start()


if __name__ == "__main__":
    main()
