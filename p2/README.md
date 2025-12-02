# Simple-FTP: Go-back-N ARQ File Transfer

CSC/ECE 573 – Internet Protocols, Project #2

## Overview

This project implements a **Simple File Transfer Protocol (Simple-FTP)** using the **Go-back-N Automatic Repeat Request (ARQ)** scheme over UDP. Unlike traditional FTP which relies on TCP for reliable data transfer, this implementation provides reliability at the application layer using the Go-back-N sliding window protocol.

## Quick Start

1. **Start the server** on the remote machine:
   ```bash
   python server.py 7735 received.txt 0.05
   ```

2. **Run the client** to transfer the file:
   ```bash
   python client.py <server-ip> 7735 test_1mb.txt 64 500
   ```

3. **Verify transfer** by comparing file sizes or contents.
   ```bash
   diff received.txt test_1mb.txt
   ```
   Expected output is empty to show that there is no difference between the files.

4. **Reset the server** after each transfer using `Ctrl-C` to clean its internal state.

## Architecture

- **Client (Sender)**: Reads a file, segments it into packets with headers, and transmits using Go-back-N
- **Server (Receiver)**: Listens for packets, validates checksums, sends ACKs, and writes data to file

## Files

| File | Description |
|------|-------------|
| `client.py` | Simple-FTP sender implementing Go-back-N protocol |
| `server.py` | Simple-FTP receiver with probabilistic packet loss |
| `packet.py` | Packet utilities (headers, checksums, parsing) |
| `test_1mb.txt` | 1MB test file for transfer experiments |

## Packet Format

### Data Packet
```
[Sequence Number: 4 bytes] [Checksum: 2 bytes] [Flags: 2 bytes] [Data: MSS bytes]
```
- **Flags**: `0x5555` (0101010101010101) indicates data packet
- **Checksum**: Internet checksum (RFC 1071) of the data portion

### ACK Packet
```
[Sequence Number: 4 bytes] [Zeros: 2 bytes] [Flags: 2 bytes]
```
- **Flags**: `0xAAAA` (1010101010101010) indicates ACK packet

## Usage

### Server
```bash
python server.py <port> <output-file> <loss-probability>
```

**Example:**
```bash
python server.py 7735 received.txt 0.05
```

**Parameters:**
- `port`: Port number to listen on (typically 7735)
- `output-file`: Name of file to write received data
- `loss-probability`: Probability of simulated packet loss (0 ≤ p < 1)

### Client
```bash
python client.py <server-host> <port> <file> <window-size> <mss>
```

**Example:**
```bash
python client.py 152.7.178.189 7735 test_1mb.txt 64 500
```

**Parameters:**
- `server-host`: Hostname or IP of the server
- `port`: Server port number (typically 7735)
- `file`: File to transfer
- `window-size (N)`: Go-back-N window size (N=1 reduces to Stop-and-Wait)
- `mss`: Maximum Segment Size in bytes

## Protocol Details

### Go-back-N Sender (Client)
1. Segments file into MSS-sized chunks
2. Maintains a sliding window of N outstanding packets
3. Starts timer when sending base packet
4. On timeout: retransmits all packets in window
5. On ACK: advances window, restarts timer if needed

### Go-back-N Receiver (Server)
1. Accepts only in-order packets with valid checksums
2. Sends cumulative ACKs for correctly received packets
3. Discards out-of-order or corrupted packets
4. Simulates packet loss based on probability p

### Timeout
Default timeout: **0.5 seconds**

## Output

### Server Output
When a packet is dropped due to simulated loss:
```
Packet loss, sequence number = X
```

### Client Output
When a timeout occurs:
```
Timeout, sequence number = Y
```

Transfer completion shows elapsed time and retransmission count.

## Experiments

A 1MB test file (`test_1mb.txt`) is included for running the experiments.

### Task 1: Effect of Window Size N
- **Fixed**: MSS = 500 bytes, p = 0.05
- **Variable**: N = 1, 2, 4, 8, 16, 32, 64, 128, 256, 512, 1024
- **Runs**: 5 transfers per N value

### Task 2: Effect of MSS
- **Fixed**: N = 64, p = 0.05
- **Variable**: MSS = 100, 200, 300, ..., 1000 bytes
- **Runs**: 5 transfers per MSS value

### Task 3: Effect of Loss Probability p
- **Fixed**: N = 64, MSS = 500 bytes
- **Variable**: p = 0.01, 0.02, ..., 0.10
- **Runs**: 5 transfers per p value

## Requirements

- Python 3.x

## Author

Frank Lin (fclin)
