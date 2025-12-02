#!/bin/bash
# Auto-restarting server script for remote execution

while true; do
    rm -f received.txt
    echo "Starting server..."
    python server.py 7735 received.txt 0.05
    echo "Server stopped. Restarting in 1 second..."
    sleep 1
done
