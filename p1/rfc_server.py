import socket
import threading
import sys

# Server Configuration
SERVER_PORT = 7734  # 
HOST = ''           # Listen on all interfaces

# Data Structures (Thread-safe lists are ideal, but standard lists work for this scope)
# active_peers = [{"hostname": str, "port": int}]
active_peers = []

# rfc_index = [{"rfc_num": int, "title": str, "hostname": str, "ttl": int}]
# Note: "ttl" is not strictly required by spec but useful for duplicate logic. 
# We will just append per spec.
rfc_index = []
index_lock = threading.Lock() # To prevent race conditions

def handle_client(conn, addr):
    """
    Handles the P2S communication for a single peer.
    """
    print(f"New connection from {addr}")
    
    # Session state to track what this specific peer has added
    # This helps in cleaning up when the peer disconnects [cite: 47]
    peer_hostname = None
    peer_upload_port = None

    try:
        while True:
            # Receive data
            data = conn.recv(4096).decode('utf-8')
            if not data:
                break # Connection closed

            # Simple parsing of the request
            # Request ends with \r\n\r\n, but we'll assume the message fits in buffer for this project
            lines = data.split('\r\n')
            if not lines:
                continue

            # Parse Request Line [cite: 91]
            # Format: METHOD <sp> RFC number <sp> version
            req_line = lines[0].split()
            if len(req_line) < 3:
                continue
                
            method = req_line[0]
            rfc_arg = req_line[1] # "RFC" literal or ignored in LIST
            version = req_line[2]

            # Headers extraction
            headers = {}
            for line in lines[1:]:
                if ": " in line:
                    key, val = line.split(": ", 1)
                    headers[key] = val

            response = ""

            if version != "P2P-CI/1.0":
                response = "P2P-CI/1.0 505 P2P-CI Version Not Supported\r\n\r\n"
            
            elif method == "ADD":
                # [cite: 94, 100-104]
                # Expected Headers: Host, Port, Title
                try:
                    rfc_num = int(req_line[1]) # Extract number from "RFC 123" -> we assume client sends just 123 or we parse it
                    # The spec example shows "ADD RFC 123", so req_line[1] is "RFC", req_line[2] is "123", req_line[3] is version
                    # Let's adjust parsing to match spec example: ADD RFC 123 P2P-CI/1.0
                    if req_line[1] == 'RFC':
                         rfc_num = int(req_line[2])
                    else:
                         rfc_num = int(req_line[1])

                    title = headers.get("Title", "Untitled")
                    host = headers.get("Host", "unknown")
                    port = int(headers.get("Port", 0))

                    # Update Session State for cleanup later
                    peer_hostname = host
                    peer_upload_port = port

                    with index_lock:
                        # Add Peer to active list if not present [cite: 40]
                        peer_record = {"hostname": host, "port": port}
                        if peer_record not in active_peers:
                            active_peers.append(peer_record)
                        
                        # Add RFC to index [cite: 42]
                        new_record = {"rfc_num": rfc_num, "title": title, "hostname": host, "port": port}
                        rfc_index.insert(0, new_record) # Insert at front [cite: 42]

                    # Response [cite: 126-128]
                    response = f"P2P-CI/1.0 200 OK\r\nRFC {rfc_num} {title} {host} {port}\r\n\r\n"
                    print(f"Peer {host} added RFC {rfc_num}")

                except Exception as e:
                    print(f"ADD Error: {e}")
                    response = "P2P-CI/1.0 400 Bad Request\r\n\r\n"

            elif method == "LOOKUP":
                # [cite: 95, 111-115]
                # Request: LOOKUP RFC 3457 P2P-CI/1.0
                try:
                    if req_line[1] == 'RFC':
                         target_rfc = int(req_line[2])
                    else:
                         target_rfc = int(req_line[1])
                    
                    matches = []
                    with index_lock:
                        for record in rfc_index:
                            if record["rfc_num"] == target_rfc:
                                matches.append(record)
                    
                    if matches:
                        response = "P2P-CI/1.0 200 OK\r\n\r\n"
                        for m in matches:
                            # Format: RFC number <sp> RFC title <sp> hostname <sp> upload port number [cite: 123]
                            response += f"RFC {m['rfc_num']} {m['title']} {m['hostname']} {m['port']}\r\n"
                    else:
                        response = "P2P-CI/1.0 404 Not Found\r\n\r\n"
                
                except:
                    response = "P2P-CI/1.0 400 Bad Request\r\n\r\n"

            elif method == "LIST":
                # [cite: 96, 117]
                # Returns all records
                with index_lock:
                    if rfc_index:
                        response = "P2P-CI/1.0 200 OK\r\n\r\n"
                        for m in rfc_index:
                            response += f"RFC {m['rfc_num']} {m['title']} {m['hostname']} {m['port']}\r\n"
                    else:
                        response = "P2P-CI/1.0 404 Not Found\r\n\r\n"
            
            else:
                response = "P2P-CI/1.0 400 Bad Request\r\n\r\n"

            conn.sendall(response.encode('utf-8'))

    except Exception as e:
        print(f"Error serving client: {e}")
    finally:
        # Cleanup [cite: 43, 47]
        # Remove all records associated with this peer
        if peer_hostname:
            with index_lock:
                # Remove from Active Peers
                active_peers[:] = [p for p in active_peers if not (p['hostname'] == peer_hostname and p['port'] == peer_upload_port)]
                # Remove from RFC Index
                initial_count = len(rfc_index)
                rfc_index[:] = [r for r in rfc_index if not (r['hostname'] == peer_hostname and r['port'] == peer_upload_port)]
                removed_count = initial_count - len(rfc_index)
                
            print(f"Peer {peer_hostname} disconnected. Removed {removed_count} records.")
        
        conn.close()

def main():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((HOST, SERVER_PORT))
        sock.listen(5)
        print(f"P2P-CI Server listening on port {SERVER_PORT}...")

        while True:
            conn, addr = sock.accept()
            # Spawn new process/thread 
            t = threading.Thread(target=handle_client, args=(conn, addr))
            t.daemon = True
            t.start()
            
    except KeyboardInterrupt:
        print("\nServer shutting down.")
        sys.exit(0)

if __name__ == "__main__":
    main()