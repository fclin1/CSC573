# P2P-CI System - Peer-to-Peer with Centralized Index

A peer-to-peer system for downloading RFCs (Requests for Comments) with a centralized index server.

## Project Structure

```
p1/
├── config.py       # Configuration constants
├── protocol.py     # Protocol message formatting/parsing
├── server.py       # Central index server
├── peer.py         # Peer application
├── rfc/            # Directory for RFC files
│   ├── rfc123.txt
│   ├── rfc2345.txt
│   └── rfc3457.txt
└── README.md       # This file
```

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only standard library)

## How to Run

### 1. Start the Central Server

Open a terminal and run:

```bash
cd p1
python server.py
```

The server will start listening on port 7734.

### 2. Start Peer Clients

Open separate terminals for each peer and run:

```bash
cd p1
python peer.py
```

Or connect to a remote server:

```bash
python peer.py <server_hostname>
```

## Peer Commands

Once a peer is running, you can use the following commands:

| Command | Description |
|---------|-------------|
| 1. ADD | Register a new RFC with the server |
| 2. LOOKUP | Find peers that have a specific RFC |
| 3. LIST | List all RFCs registered on the server |
| 4. GET | Download an RFC from another peer |
| 5. LOCAL | List local RFC files |
| 6. QUIT | Exit the program |

## Testing with Multiple Peers

1. Start the server in one terminal
2. Start Peer A in another terminal (it will auto-register its local RFCs)
3. Start Peer B in a third terminal
4. From Peer B, use LOOKUP or LIST to find RFCs
5. Use GET to download an RFC from Peer A

## Protocol Details

### P2S Protocol (Peer-to-Server)

Methods:
- **ADD**: Register an RFC with the server
- **LOOKUP**: Find peers with a specific RFC  
- **LIST**: Get all RFCs in the index

### P2P Protocol (Peer-to-Peer)

Methods:
- **GET**: Download an RFC from another peer

Status Codes:
- 200 OK
- 400 Bad Request
- 404 Not Found
- 505 P2P-CI Version Not Supported

## Notes

- The server uses port 7734 (well-known port)
- Each peer runs an upload server on a dynamically assigned port
- RFCs are stored as text files in the `rfc/` directory
- File naming convention: `rfc<number>.txt` (e.g., `rfc123.txt`)
