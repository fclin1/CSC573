# P2P-CI System Makefile
# Usage: make <target>

.PHONY: all server peer peer-a peer-b peer-empty clean help

# Default target - show help
all: help

# Run the central server on port 7734
server:
	python server.py

# Run a peer client with default RFC directory (./rfc)
peer:
	python peer.py

# Run Peer A with rfc_a directory (has RFC 123)
peer-a:
	python peer.py -d rfc_a

# Run Peer B with rfc_b directory (has RFC 2345)
peer-b:
	python peer.py -d rfc_b

# Run a peer with empty RFC directory (for testing downloads)
peer-empty:
	@mkdir -p rfc_empty
	python peer.py -d rfc_empty

# Clean up temporary files and downloaded RFCs (keep original RFCs)
clean:
	rm -rf rfc_empty __pycache__
	@find rfc_a -type f ! -name 'rfc123.txt' -delete 2>/dev/null || true
	@find rfc_b -type f ! -name 'rfc2345.txt' -delete 2>/dev/null || true

# Display help information
help:
	@echo "P2P-CI System - Makefile Commands"
	@echo "=================================="
	@echo ""
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  server      - Start the central index server (port 7734)"
	@echo "  peer        - Start a peer client (uses ./rfc directory)"
	@echo "  peer-a      - Start Peer A (uses ./rfc_a, has RFC 123)"
	@echo "  peer-b      - Start Peer B (uses ./rfc_b, has RFC 2345)"
	@echo "  peer-empty  - Start a peer with empty RFC directory"
	@echo "  clean       - Remove temporary files and downloaded RFCs"
	@echo "  help        - Show this help message"
	@echo ""
	@echo "Demo workflow:"
	@echo "  Terminal 1: make server"
	@echo "  Terminal 2: make peer-a"
	@echo "  Terminal 3: make peer-b"
