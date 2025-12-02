# Peer application for P2P-CI
# Runs upload server, connects to central server, downloads RFCs from other peers

import socket
import threading
import os
import argparse
from datetime import datetime
from config import SERVER_PORT, VERSION, RFC_DIR
from protocol import (
    build_add_request, build_lookup_request, build_list_request,
    build_get_request, build_get_response,
    parse_p2s_response, parse_p2p_request, parse_p2p_response,
    get_os_info, CRLF
)


class UploadServer:
    """Handles RFC download requests from other peers."""
    
    def __init__(self, rfc_dir):
        self.rfc_dir = rfc_dir
        self.server_socket = None
        self.port = 0
        self.running = False
    
    def start(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', 0))
        self.port = self.server_socket.getsockname()[1]
        self.server_socket.listen(5)
        self.running = True
        
        t = threading.Thread(target=self._accept_loop)
        t.daemon = True
        t.start()
        print(f"[Peer] Upload server started on port {self.port}")
    
    def stop(self):
        self.running = False
        if self.server_socket:
            self.server_socket.close()
    
    def _accept_loop(self):
        while self.running:
            try:
                client_sock, addr = self.server_socket.accept()
                print(f"[Peer] Upload connection from {addr}")
                t = threading.Thread(target=self._handle_download, args=(client_sock,))
                t.daemon = True
                t.start()
            except socket.error:
                pass
    
    def _handle_download(self, client_sock):
        try:
            # Receive request
            data = b""
            while b"\r\n\r\n" not in data:
                chunk = client_sock.recv(4096)
                if not chunk:
                    return
                data += chunk
            
            request_str = data.decode()
            print(f"[Peer] Received GET request:\n{request_str.strip()}")
            
            req = parse_p2p_request(request_str)
            if not req:
                client_sock.send(build_get_response(400).encode())
                return
            
            if req['version'] != VERSION:
                client_sock.send(build_get_response(505).encode())
                return
            
            rfc_num = req['rfc_number']
            rfc_file = os.path.join(self.rfc_dir, f"rfc{rfc_num}.txt")
            
            if not os.path.exists(rfc_file):
                client_sock.send(build_get_response(404).encode())
                print(f"[Peer] RFC {rfc_num} not found")
                return
            
            with open(rfc_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            mtime = os.path.getmtime(rfc_file)
            last_mod = datetime.utcfromtimestamp(mtime).strftime("%a, %d %b %Y %H:%M:%S GMT")
            
            client_sock.send(build_get_response(200, content, last_mod).encode())
            print(f"[Peer] Sent RFC {rfc_num} ({len(content)} bytes)")
            
        except Exception as e:
            print(f"[Peer] Upload error: {e}")
        finally:
            client_sock.close()


class Peer:
    def __init__(self, server_host='localhost', server_port=SERVER_PORT, rfc_dir=None):
        self.server_host = server_host
        self.server_port = server_port
        self.server_socket = None
        self.hostname = socket.gethostname()
        self.rfc_dir = rfc_dir or os.path.join(os.path.dirname(__file__), RFC_DIR)
        
        if not os.path.exists(self.rfc_dir):
            os.makedirs(self.rfc_dir)
        
        self.upload_server = UploadServer(self.rfc_dir)
        self.upload_port = 0
    
    def connect(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.connect((self.server_host, self.server_port))
        print(f"[Peer] Connected to server at port {self.server_port}")
    
    def disconnect(self):
        if self.server_socket:
            self.server_socket.close()
            self.server_socket = None
        print("[Peer] Disconnected from server")
    
    def start(self):
        self.upload_server.start()
        self.upload_port = self.upload_server.port
        self.connect()
        self._register_with_server()
        self._register_local_rfcs()
    
    def _register_with_server(self):
        """Send initial LIST to register even if no RFCs."""
        request = build_list_request(self.hostname, self.upload_port)
        self.server_socket.send(request.encode())
        # Receive silently
        data = b""
        while b"\r\n\r\n" not in data:
            chunk = self.server_socket.recv(4096)
            if not chunk:
                break
            data += chunk
    
    def stop(self):
        self.upload_server.stop()
        self.disconnect()
        print("[Peer] Peer stopped")
    
    def _send_request(self, request):
        self.server_socket.send(request.encode())
        data = b""
        while True:
            chunk = self.server_socket.recv(4096)
            if not chunk:
                break
            data += chunk
            if b"\r\n\r\n" in data:
                break
        return data.decode()
    
    def _register_local_rfcs(self):
        if not os.path.exists(self.rfc_dir):
            return
        for fname in os.listdir(self.rfc_dir):
            if fname.startswith('rfc') and fname.endswith('.txt'):
                try:
                    rfc_num = int(fname[3:-4])
                    title = self._get_title(os.path.join(self.rfc_dir, fname))
                    self.add_rfc(rfc_num, title)
                except ValueError:
                    pass
    
    def _get_title(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        return line[:100]
        except:
            pass
        return os.path.basename(filepath)
    
    def add_rfc(self, rfc_num, title):
        request = build_add_request(rfc_num, self.hostname, self.upload_port, title)
        print(f"[Peer] Registering RFC {rfc_num}: {title}")
        response = self._send_request(request)
        print(response.strip())
        return response
    
    def lookup_rfc(self, rfc_num, title=""):
        request = build_lookup_request(rfc_num, self.hostname, self.upload_port, title)
        print(f"\n[Peer] Looking up RFC {rfc_num}")
        print(f"Request:\n{request.strip()}")
        response = self._send_request(request)
        print(f"Response:\n{response.strip()}")
        return parse_p2s_response(response)
    
    def list_rfcs(self):
        request = build_list_request(self.hostname, self.upload_port)
        print(f"\n[Peer] Sending LIST ALL request")
        print(f"Request:\n{request.strip()}")
        response = self._send_request(request)
        print(f"Response:\n{response.strip()}")
        return parse_p2s_response(response)
    
    def download_rfc(self, rfc_num, peer_host, peer_port):
        print(f"\n[Peer] Downloading RFC {rfc_num} from {peer_host}:{peer_port}")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((peer_host, peer_port))
            
            request = build_get_request(rfc_num, peer_host)
            print(f"Request:\n{request.strip()}")
            sock.send(request.encode())
            
            data = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                data += chunk
            sock.close()
            
            response = parse_p2p_response(data.decode())
            
            if response and response['status_code'] == 200:
                print(f"Response:")
                print(f"{VERSION} {response['status_code']} {response['phrase']}")
                for k, v in response['headers'].items():
                    print(f"{k}: {v}")
                print(f"<RFC {rfc_num} content - {len(response['data'])} bytes>")
                
                rfc_file = os.path.join(self.rfc_dir, f"rfc{rfc_num}.txt")
                with open(rfc_file, 'w', encoding='utf-8') as f:
                    f.write(response['data'])
                
                print(f"\n[Peer] Downloaded RFC {rfc_num} successfully")
                print(f"[Peer] Saved to {rfc_file}")
                
                # Register with server
                title = self._get_title(rfc_file)
                self.add_rfc(rfc_num, title)
                return True
            else:
                print(f"[Peer] Download failed")
                return False
                
        except Exception as e:
            print(f"[Peer] Download error: {e}")
            return False
    
    def interactive_menu(self):
        print("\n" + "=" * 50)
        print("P2P-CI Peer Client")
        print("=" * 50)
        print(f"Hostname: {self.hostname}")
        print(f"Upload port: {self.upload_port}")
        print(f"RFC directory: {self.rfc_dir}")
        print("=" * 50)
        
        while True:
            print("\nCommands:")
            print("  1. ADD      - Register an RFC")
            print("  2. LOOKUP   - Find peers with RFC")
            print("  3. LIST ALL - List all RFCs")
            print("  4. GET      - Download RFC")
            print("  5. LOCAL    - List local RFCs")
            print("  6. QUIT     - Exit")
            
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
                    rfc_num = int(input("Enter RFC number: "))
                    self.lookup_rfc(rfc_num)
                except ValueError:
                    print("Invalid RFC number")
            
            elif choice == '3':
                self.list_rfcs()
            
            elif choice == '4':
                try:
                    rfc_num = int(input("Enter RFC number: "))
                    result = self.lookup_rfc(rfc_num)
                    if result and result['status_code'] == 200 and result['data_lines']:
                        parts = result['data_lines'][0].split()
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
                    for f in sorted(files) if files else ["  (none)"]:
                        print(f"  {f}")
                else:
                    print("  (directory not found)")
            
            elif choice == '6' or choice.lower() == 'quit':
                break
            else:
                print("Invalid command")


def main():
    parser = argparse.ArgumentParser(description='P2P-CI Peer')
    parser.add_argument('-s', '--server', default='localhost', help='Server host')
    parser.add_argument('-d', '--rfc-dir', default=None, help='RFC directory')
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
