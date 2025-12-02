"""
Peer application for P2P-CI system.

Each peer:
- Runs an upload server on a dynamic port to serve RFC files
- Connects to the central server to register and query
- Can download RFCs from other peers
"""

import socket
import threading
import os
import sys
from datetime import datetime
from config import SERVER_PORT, VERSION, RFC_DIR
from protocol import (
    build_add_request, build_lookup_request, build_list_request,
    build_get_request, build_get_response,
    parse_p2s_response, parse_p2p_request, parse_p2p_response,
    get_os_info, CRLF
)


class UploadServer:
    """Server that handles RFC download requests from other peers."""
    
    def __init__(self, rfc_dir):
        self.rfc_dir = rfc_dir
        self.server_socket = None
        self.port = 0
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the upload server on an available port."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', 0))  # Bind to any available port
        self.port = self.server_socket.getsockname()[1]
        self.server_socket.listen(5)
        self.running = True
        
        self.thread = threading.Thread(target=self._accept_connections)
        self.thread.daemon = True
        self.thread.start()
        
        print(f"[Peer] Upload server started on port {self.port}")
    
    def stop(self):
        """Stop the upload server."""
        self.running = False
        if self.server_socket:
            self.server_socket.close()
    
    def _accept_connections(self):
        """Accept and handle incoming connections."""
        while self.running:
            try:
                client_socket, client_address = self.server_socket.accept()
                print(f"[Peer] Upload connection from {client_address}")
                
                # Handle in a new thread
                handler = threading.Thread(
                    target=self._handle_download,
                    args=(client_socket, client_address)
                )
                handler.daemon = True
                handler.start()
            except socket.error:
                if self.running:
                    pass  # Socket closed during shutdown
    
    def _handle_download(self, client_socket, client_address):
        """Handle a download request from another peer."""
        try:
            # Receive the request
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = client_socket.recv(4096)
                if not chunk:
                    return
                data += chunk
            
            request_str = data.decode('utf-8')
            print(f"[Peer] Received GET request:")
            print(request_str.strip())
            
            # Parse the P2P GET request
            request = parse_p2p_request(request_str)
            if not request:
                response = build_get_response(400)
                client_socket.send(response.encode('utf-8'))
                return
            
            if request['version'] != VERSION:
                response = build_get_response(505)
                client_socket.send(response.encode('utf-8'))
                return
            
            rfc_number = request['rfc_number']
            rfc_file = os.path.join(self.rfc_dir, f"rfc{rfc_number}.txt")
            
            if not os.path.exists(rfc_file):
                response = build_get_response(404)
                client_socket.send(response.encode('utf-8'))
                print(f"[Peer] RFC {rfc_number} not found")
                return
            
            # Read the RFC file
            with open(rfc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Get last modified time
            mtime = os.path.getmtime(rfc_file)
            last_modified = datetime.utcfromtimestamp(mtime).strftime(
                "%a, %d %b %Y %H:%M:%S GMT"
            )
            
            response = build_get_response(200, content, last_modified)
            client_socket.send(response.encode('utf-8'))
            print(f"[Peer] Sent RFC {rfc_number} ({len(content)} bytes)")
            
        except Exception as e:
            print(f"[Peer] Upload error: {e}")
        finally:
            client_socket.close()


class Peer:
    """Main peer application."""
    
    def __init__(self, server_host='localhost', server_port=SERVER_PORT, rfc_dir=None):
        self.server_host = server_host
        self.server_port = server_port
        self.server_socket = None
        self.hostname = socket.gethostname()
        
        # Set up RFC directory (use provided or default)
        if rfc_dir:
            self.rfc_dir = rfc_dir
        else:
            self.rfc_dir = os.path.join(os.path.dirname(__file__), RFC_DIR)
        if not os.path.exists(self.rfc_dir):
            os.makedirs(self.rfc_dir)
        
        # Upload server
        self.upload_server = UploadServer(self.rfc_dir)
        self.upload_port = 0
    
    def connect(self):
        """Connect to the central server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.connect((self.server_host, self.server_port))
        print(f"[Peer] Connected to server at port {self.server_port}")
    
    def disconnect(self):
        """Disconnect from the central server."""
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        print("[Peer] Disconnected from server")
    
    def start(self):
        """Start the peer - upload server and connect to central server."""
        # Start upload server
        self.upload_server.start()
        self.upload_port = self.upload_server.port
        
        # Connect to central server
        self.connect()
        
        # Send initial LIST request to register with server (even if no RFCs)
        # This ensures the server knows about this peer
        self.send_initial_registration()
        
        # Register existing RFCs
        self.register_local_rfcs()
    
    def send_initial_registration(self):
        """Send initial request to register peer with server."""
        from protocol import build_list_request
        request = build_list_request(self.hostname, self.upload_port)
        # Just send and receive, don't print (silent registration)
        self.server_socket.send(request.encode('utf-8'))
        # Receive response but don't display it
        data = b""
        while True:
            chunk = self.server_socket.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\r\n\r\n" in data:
                break
    
    def stop(self):
        """Stop the peer."""
        self.upload_server.stop()
        self.disconnect()
        print("[Peer] Peer stopped")
    
    def send_request(self, request):
        """Send a request to the central server and receive response."""
        self.server_socket.send(request.encode('utf-8'))
        
        # Receive response
        data = b""
        while True:
            chunk = self.server_socket.recv(4096)
            if not chunk:
                break
            data += chunk
            # Check for complete response (has header and possibly data)
            if b"\r\n\r\n" in data:
                # For P2S responses, data ends with empty line
                decoded = data.decode('utf-8')
                if decoded.count('\r\n\r\n') >= 1:
                    break
        
        return data.decode('utf-8')
    
    def register_local_rfcs(self):
        """Register all local RFC files with the server."""
        if not os.path.exists(self.rfc_dir):
            return
        
        for filename in os.listdir(self.rfc_dir):
            if filename.startswith('rfc') and filename.endswith('.txt'):
                try:
                    rfc_number = int(filename[3:-4])
                    title = self.get_rfc_title(os.path.join(self.rfc_dir, filename))
                    self.add_rfc(rfc_number, title)
                except ValueError:
                    continue
    
    def get_rfc_title(self, filepath):
        """Extract title from RFC file (first non-empty line or filename)."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        return line[:100]  # Limit title length
        except:
            pass
        return os.path.basename(filepath)
    
    def add_rfc(self, rfc_number, title):
        """Send ADD request to register an RFC with the server."""
        request = build_add_request(rfc_number, self.hostname, self.upload_port, title)
        print(f"[Peer] Registering RFC {rfc_number}: {title}")
        response = self.send_request(request)
        print(response.strip())
        return response
    
    def lookup_rfc(self, rfc_number, title=""):
        """Send LOOKUP request to find peers with specified RFC."""
        request = build_lookup_request(rfc_number, self.hostname, self.upload_port, title)
        print(f"\n[Peer] Looking up RFC {rfc_number}")
        print(f"Request:")
        print(request.strip())
        response = self.send_request(request)
        print(f"Response:")
        print(response.strip())
        return parse_p2s_response(response)
    
    def list_rfcs(self):
        """Send LIST ALL request to get all RFCs from server."""
        request = build_list_request(self.hostname, self.upload_port)
        print(f"\n[Peer] Sending LIST ALL request")
        print(f"Request:")
        print(request.strip())
        response = self.send_request(request)
        print(f"Response:")
        print(response.strip())
        return parse_p2s_response(response)
    
    def download_rfc(self, rfc_number, peer_hostname, peer_port):
        """Download an RFC from another peer."""
        print(f"\n[Peer] Downloading RFC {rfc_number} from {peer_hostname}:{peer_port}")
        
        try:
            # Connect to the peer's upload server
            peer_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            peer_socket.connect((peer_hostname, peer_port))
            
            # Send GET request
            request = build_get_request(rfc_number, peer_hostname)
            print(f"Request:")
            print(request.strip())
            peer_socket.send(request.encode('utf-8'))
            
            # Receive response
            data = b""
            while True:
                chunk = peer_socket.recv(4096)
                if not chunk:
                    break
                data += chunk
            
            peer_socket.close()
            
            response_str = data.decode('utf-8')
            response = parse_p2p_response(response_str)
            
            if response and response['status_code'] == 200:
                # Print the response headers
                print(f"Response:")
                # Reconstruct header portion for display
                print(f"{VERSION} {response['status_code']} {response['phrase']}")
                for key, val in response['headers'].items():
                    print(f"{key}: {val}")
                print(f"<RFC {rfc_number} content - {len(response['data'])} bytes>")
                
                # Save the RFC file
                rfc_file = os.path.join(self.rfc_dir, f"rfc{rfc_number}.txt")
                with open(rfc_file, 'w', encoding='utf-8') as f:
                    f.write(response['data'])
                
                print(f"\n[Peer] Downloaded RFC {rfc_number} successfully")
                print(f"[Peer] Saved to {rfc_file}")
                
                # Register the new RFC with the server
                title = self.get_rfc_title(rfc_file)
                self.add_rfc(rfc_number, title)
                
                return True
            else:
                print(f"[Peer] Download failed: {response_str[:200] if response_str else 'No response'}")
                return False
                
        except Exception as e:
            print(f"[Peer] Download error: {e}")
            return False
    
    def interactive_menu(self):
        """Run interactive command menu."""
        print("\n" + "=" * 50)
        print("P2P-CI Peer Client")
        print("=" * 50)
        print(f"Hostname: {self.hostname}")
        print(f"Upload port: {self.upload_port}")
        print(f"RFC directory: {self.rfc_dir}")
        print("=" * 50)
        
        while True:
            print("\nCommands:")
            print("  1. ADD      - Register an RFC with the server")
            print("  2. LOOKUP   - Find peers with a specific RFC")
            print("  3. LIST ALL - List all RFCs in the system")
            print("  4. GET      - Download an RFC from a peer")
            print("  5. LOCAL    - List local RFC files")
            print("  6. QUIT     - Exit the program")
            
            choice = input("\nEnter command (1-6): ").strip()
            
            if choice == '1':
                try:
                    rfc_num = int(input("Enter RFC number: "))
                    title = input("Enter RFC title: ")
                    self.add_rfc(rfc_num, title)
                except ValueError:
                    print("Invalid RFC number")
            
            elif choice == '2':
                try:
                    rfc_num = int(input("Enter RFC number to lookup: "))
                    self.lookup_rfc(rfc_num)
                except ValueError:
                    print("Invalid RFC number")
            
            elif choice == '3':
                self.list_rfcs()
            
            elif choice == '4':
                try:
                    rfc_num = int(input("Enter RFC number to download: "))
                    # First lookup the RFC
                    result = self.lookup_rfc(rfc_num)
                    if result and result['status_code'] == 200 and result['data_lines']:
                        # Parse first available peer
                        line = result['data_lines'][0]
                        parts = line.split()
                        # Format: RFC <num> <title...> <hostname> <port>
                        peer_host = parts[-2]
                        peer_port = int(parts[-1])
                        self.download_rfc(rfc_num, peer_host, peer_port)
                    else:
                        print("RFC not found on any peer")
                except ValueError:
                    print("Invalid input")
                except Exception as e:
                    print(f"Error: {e}")
            
            elif choice == '5':
                print("\nLocal RFC files:")
                if os.path.exists(self.rfc_dir):
                    files = [f for f in os.listdir(self.rfc_dir) if f.endswith('.txt')]
                    if files:
                        for f in sorted(files):
                            print(f"  {f}")
                    else:
                        print("  (none)")
                else:
                    print("  (RFC directory does not exist)")
            
            elif choice == '6' or choice.lower() == 'quit':
                break
            
            else:
                print("Invalid command. Please enter 1-6.")


def main():
    """Main entry point for the peer."""
    import argparse
    
    parser = argparse.ArgumentParser(description='P2P-CI Peer Application')
    parser.add_argument('--server', '-s', default='localhost', 
                        help='Server hostname (default: localhost)')
    parser.add_argument('--rfc-dir', '-d', default=None,
                        help='RFC directory path (default: ./rfc)')
    args = parser.parse_args()
    
    print("=" * 50)
    print("P2P-CI Peer Application")
    print("=" * 50)
    
    peer = Peer(server_host=args.server, rfc_dir=args.rfc_dir)
    
    try:
        peer.start()
        peer.interactive_menu()
    except ConnectionRefusedError:
        print(f"[ERROR] Could not connect to server at {args.server}:{SERVER_PORT}")
        print("[ERROR] Make sure the server is running.")
    except KeyboardInterrupt:
        print("\n[Peer] Interrupted")
    finally:
        peer.stop()


if __name__ == "__main__":
    main()
