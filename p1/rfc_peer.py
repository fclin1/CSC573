import socket
import threading
import os
import platform
import sys
import time
from datetime import datetime

# Configuration
SERVER_HOST = 'localhost' # Change this if server is on another machine
SERVER_PORT = 7734
RFC_DIR = 'rfc_files'     # Folder containing local RFCs

def get_local_ip():
    # Helper to get actual hostname/IP accessible from outside
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

# -----------------------------------------------------------------------------
# P2P UPLOAD SERVER IMPLEMENTATION
# -----------------------------------------------------------------------------

def handle_upload_request(conn):
    """
    Handles incoming GET requests from other peers[cite: 55].
    """
    try:
        data = conn.recv(1024).decode('utf-8')
        if not data: 
            return

        lines = data.split('\r\n')
        req_line = lines[0].split()
        
        # Expecting: GET RFC 1234 P2P-CI/1.0 [cite: 64]
        if len(req_line) < 4 or req_line[0] != 'GET':
            header = "P2P-CI/1.0 400 Bad Request\r\n\r\n"
            conn.sendall(header.encode('utf-8'))
            return

        rfc_num = req_line[2]
        filename = f"rfc{rfc_num}.txt"
        filepath = os.path.join(RFC_DIR, filename)

        if os.path.isfile(filepath):
            # 200 OK [cite: 75, 81]
            with open(filepath, 'r') as f:
                content = f.read()
            
            # Metadata for Headers [cite: 79]
            last_modified = time.ctime(os.path.getmtime(filepath))
            os_name = platform.system() + " " + platform.release()
            content_length = len(content)
            date_now = datetime.now().strftime("%a, %d %b %Y %H:%M:%S GMT")

            response = (
                f"P2P-CI/1.0 200 OK\r\n"
                f"Date: {date_now}\r\n"
                f"OS: {os_name}\r\n"
                f"Last-Modified: {last_modified}\r\n"
                f"Content-Length: {content_length}\r\n"
                f"Content-Type: text/plain\r\n\r\n"
                f"{content}"
            )
            conn.sendall(response.encode('utf-8'))
        else:
            # 404 Not Found [cite: 77]
            response = "P2P-CI/1.0 404 Not Found\r\n\r\n"
            conn.sendall(response.encode('utf-8'))

    except Exception as e:
        print(f"Upload Server Error: {e}")
    finally:
        conn.close() # [cite: 26]

def start_upload_server(upload_socket):
    while True:
        try:
            conn, addr = upload_socket.accept()
            t = threading.Thread(target=handle_upload_request, args=(conn,))
            t.start()
        except:
            break

# -----------------------------------------------------------------------------
# CLIENT IMPLEMENTATION (P2S and P2P Download)
# -----------------------------------------------------------------------------

def send_p2s_request(sock, method, arg, headers):
    """
    Constructs and sends a P2S request[cite: 90].
    """
    # Format: method <sp> RFC number <sp> version
    if method == "LIST":
        # LIST uses "ALL" or empty arg usually, spec says "LIST ALL" in example [cite: 117]
        req_line = f"{method} ALL P2P-CI/1.0\r\n"
    else:
        req_line = f"{method} RFC {arg} P2P-CI/1.0\r\n"
    
    msg = req_line
    for k, v in headers.items():
        msg += f"{k}: {v}\r\n"
    msg += "\r\n"
    
    sock.sendall(msg.encode('utf-8'))
    
    # Receive response
    response = sock.recv(8192).decode('utf-8')
    return response

def download_rfc(rfc_num, peer_host, peer_port):
    """
    Connects to another peer and downloads an RFC[cite: 53].
    """
    print(f"Initiating download for RFC {rfc_num} from {peer_host}:{peer_port}...")
    try:
        # Create connection to Peer [cite: 25]
        p_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        p_sock.connect((peer_host, int(peer_port)))
        
        # Construct Request [cite: 58-66]
        req = (
            f"GET RFC {rfc_num} P2P-CI/1.0\r\n"
            f"Host: {peer_host}\r\n"
            f"OS: {platform.system()}\r\n\r\n"
        )
        p_sock.sendall(req.encode('utf-8'))
        
        # Receive Response
        # We need to separate headers from body
        data = b""
        while True:
            chunk = p_sock.recv(4096)
            if not chunk: break
            data += chunk
        
        p_sock.close() # [cite: 26]

        raw_response = data.decode('utf-8', errors='ignore')
        
        # Split headers and body
        if "\r\n\r\n" in raw_response:
            header_part, body_part = raw_response.split("\r\n\r\n", 1)
            
            # Check for 200 OK [cite: 75]
            if "200 OK" in header_part:
                # Save file
                filename = f"rfc{rfc_num}.txt"
                filepath = os.path.join(RFC_DIR, filename)
                with open(filepath, 'w') as f:
                    f.write(body_part)
                print(f"Successfully downloaded {filename}")
                return True
            else:
                print("Download failed. Server response:")
                print(header_part)
                return False
        else:
            print("Invalid response format from peer.")
            return False

    except Exception as e:
        print(f"P2P Download Error: {e}")
        return False

def main():
    # Ensure RFC directory exists
    if not os.path.exists(RFC_DIR):
        os.makedirs(RFC_DIR)
        print(f"Created directory {RFC_DIR}. Please put RFC files there.")

    # 1. Initialize Upload Server (Bind to ephemeral port) [cite: 49]
    upload_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    upload_sock.bind(('', 0)) # OS picks port
    upload_port = upload_sock.getsockname()[1]
    upload_sock.listen(5)
    
    # Start upload server thread
    u_thread = threading.Thread(target=start_upload_server, args=(upload_sock,))
    u_thread.daemon = True
    u_thread.start()
    
    my_hostname = socket.gethostname() # [cite: 102]
    # In a real network, use get_local_ip() for my_hostname if DNS isn't set up
    
    print(f"Upload Server started at {my_hostname}:{upload_port}")

    # 2. Connect to Central Server [cite: 50]
    try:
        server_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_conn.connect((SERVER_HOST, SERVER_PORT))
    except ConnectionRefusedError:
        print("Could not connect to Central Server. Is it running?")
        sys.exit(1)

    # 3. Initial Registration: ADD all local RFCs [cite: 41]
    # We assume files are named "rfc<number>.txt"
    files = [f for f in os.listdir(RFC_DIR) if f.startswith('rfc') and f.endswith('.txt')]
    for f in files:
        # Extract number
        try:
            num = f.replace('rfc', '').replace('.txt', '')
            title = f"Title of {f}" # Placeholder title
            
            headers = {
                "Host": my_hostname,
                "Port": upload_port,
                "Title": title
            }
            resp = send_p2s_request(server_conn, "ADD", num, headers)
            print(f"Auto-adding {f}: {resp.splitlines()[0]}")
        except:
            pass

    # 4. User Interface Loop
    print("\n--- Command Menu ---")
    print("1. ADD (Manually add an RFC record)")
    print("2. LOOKUP (Find a peer with an RFC)")
    print("3. LIST (List all RFCs)")
    print("4. DOWNLOAD (Get RFC from peer)")
    print("5. EXIT")
    
    while True:
        choice = input("\nEnter command (1-5): ").strip()
        
        if choice == '1': # ADD
            rfc_num = input("Enter RFC Number: ")
            title = input("Enter RFC Title: ")
            headers = {
                "Host": my_hostname,
                "Port": upload_port,
                "Title": title
            }
            resp = send_p2s_request(server_conn, "ADD", rfc_num, headers)
            print(resp)
            
        elif choice == '2': # LOOKUP
            rfc_num = input("Enter RFC Number: ")
            headers = {
                "Host": my_hostname,
                "Port": upload_port,
                "Title": "Lookup"
            }
            resp = send_p2s_request(server_conn, "LOOKUP", rfc_num, headers)
            print(resp)
            
        elif choice == '3': # LIST
            headers = {
                "Host": my_hostname,
                "Port": upload_port
            }
            resp = send_p2s_request(server_conn, "LIST", "", headers)
            print(resp)
            
        elif choice == '4': # DOWNLOAD
            # Usually user does LOOKUP first to get Host/Port
            rfc_num = input("Enter RFC Number to download: ")
            t_host = input("Enter Target Hostname: ")
            t_port = input("Enter Target Port: ")
            
            success = download_rfc(rfc_num, t_host, t_port)
            if success:
                # If download successful, we must ADD it to server [cite: 110]
                headers = {
                    "Host": my_hostname,
                    "Port": upload_port,
                    "Title": f"Downloaded RFC {rfc_num}"
                }
                send_p2s_request(server_conn, "ADD", rfc_num, headers)
                print("Automatically registered new RFC with server.")

        elif choice == '5': # EXIT
            print("Exiting...")
            server_conn.close() # [cite: 53]
            sys.exit(0)
        else:
            print("Invalid command.")

if __name__ == "__main__":
    main()