# P2P-CI System - Peer-to-Peer with Centralized Index

A peer-to-peer system for downloading RFCs (Requests for Comments) with a centralized index server.

## Project Structure

```
p1/
├── config.py       # Configuration constants
├── protocol.py     # Protocol message formatting/parsing
├── server.py       # Central index server
├── peer.py         # Peer application
├── Makefile        # Build automation with convenient targets
├── rfc/            # Default RFC directory (full collection)
│   ├── rfc123.txt
│   ├── rfc2345.txt
│   └── rfc3457.txt
├── rfc_a/          # Peer A's RFC directory (has RFC 123)
│   └── rfc123.txt
├── rfc_b/          # Peer B's RFC directory (has RFC 2345)
│   └── rfc2345.txt
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
python3 server.py
```

The server will start listening on port 7734.

### 2. Start Peer Clients

Open separate terminals for each peer and run:

```bash
cd p1
python3 peer.py
```

Or connect to a remote server:

```bash
python3 peer.py <server_hostname>
```

## Quick Start with Makefile

The easiest way to run the system is using the provided Makefile:

### View Available Commands

```bash
make help
```

### Running a Demo with Pre-configured Peers

Open **three separate terminals** and run:

**Terminal 1 - Start the server:**
```bash
make server
```

**Terminal 2 - Start Peer A (has RFC 123):**
```bash
make peer-a
```

**Terminal 3 - Start Peer B (has RFC 2345):**
```bash
make peer-b
```

Now you can test peer-to-peer transfers:
- From Peer B, use command `2` (LOOKUP) to find RFC 123
- From Peer B, use command `4` (GET) to download RFC 123 from Peer A
- Vice versa with Peer A downloading RFC 2345 from Peer B

### Available Makefile Targets

| Target | Description |
|--------|-------------|
| `make server` | Start the central index server (port 7734) |
| `make peer` | Start a peer with the full RFC collection (./rfc) |
| `make peer-a` | Start Peer A with rfc_a directory (has RFC 123) |
| `make peer-b` | Start Peer B with rfc_b directory (has RFC 2345) |
| `make peer-empty` | Start a peer with empty RFC directory |
| `make clean` | Remove temporary files and downloaded RFCs |
| `make help` | Show help message |

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

### Demo Workflow Example with Pre-configured Peers

After starting the server and both peers using `make peer-a` and `make peer-b`:

1. **From Peer B's terminal:**
   - Choose option `3` (LIST) to see all available RFCs
   - Choose option `2` (LOOKUP) and enter `123` to find who has RFC 123
   - Choose option `4` (GET) and enter `123` to download it from Peer A
   - Choose option `5` (LOCAL) to verify the file was downloaded

2. **From Peer A's terminal:**
   - Choose option `2` (LOOKUP) and enter `2345` to find who has RFC 2345
   - Choose option `4` (GET) and enter `2345` to download it from Peer B
   - Choose option `5` (LOCAL) to verify the download

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
