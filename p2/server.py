"""
Simple-FTP Server (Receiver) - Go-back-N ARQ

Usage: python server.py <port> <output-file> <loss-probability>
"""

import socket
import sys
import random
from packet import parse_packet, make_ack_packet, is_valid_data


def run_server(port: int, output_filename: str, loss_probability: float):
    """Receive file using Go-back-N protocol."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('', port))
    
    print(f"Listening on port {port}, writing to '{output_filename}', loss={loss_probability}")
    
    expected_sequence_number = 0
    
    with open(output_filename, 'wb') as output_file:
        while True:
            try:
                packet_data, client_address = server_socket.recvfrom(65535)
                parsed_packet = parse_packet(packet_data)
                if not parsed_packet:
                    continue
                
                sequence_number, received_checksum, flags, payload = parsed_packet
                
                # Simulate packet loss
                if random.random() <= loss_probability:
                    print(f"Packet loss, sequence number = {sequence_number}")
                    continue
                
                # Validate packet
                if not is_valid_data(sequence_number, received_checksum, flags, payload):
                    continue
                
                if sequence_number == expected_sequence_number:
                    # In-order: accept data, send ACK, advance
                    output_file.write(payload)
                    output_file.flush()
                    server_socket.sendto(make_ack_packet(sequence_number), client_address)
                    expected_sequence_number += 1
                elif expected_sequence_number > 0:
                    # Out-of-order: resend last ACK
                    server_socket.sendto(make_ack_packet(expected_sequence_number - 1), client_address)
                    
            except KeyboardInterrupt:
                print("\nShutting down...")
                break
    
    server_socket.close()


def main():
    if len(sys.argv) != 4:
        print("Usage: python server.py <port> <output-file> <loss-probability>")
        sys.exit(1)
    
    port = int(sys.argv[1])
    output_filename = sys.argv[2]
    loss_probability = float(sys.argv[3])
    
    if not (0 <= loss_probability < 1):
        sys.exit("Error: loss probability must be in [0, 1)")
    
    run_server(port, output_filename, loss_probability)


if __name__ == "__main__":
    main()
