"""
Simple-FTP Client (Sender) - Go-back-N ARQ

Usage: python client.py <host> <port> <file> <window-size> <mss>
"""

import socket
import sys
import time
from packet import make_data_packet, parse_packet, is_ack, HEADER_SIZE

TIMEOUT = 0.5  # seconds


def create_packets(input_filename: str, max_segment_size: int) -> list[bytes]:
    """Read file and segment into packets."""
    with open(input_filename, 'rb') as input_file:
        file_data = input_file.read()
    
    packet_list = []
    for offset in range(0, len(file_data), max_segment_size):
        sequence_number = len(packet_list)
        segment_data = file_data[offset:offset + max_segment_size]
        packet_list.append(make_data_packet(sequence_number, segment_data))
    
    print(f"Loaded '{input_filename}': {len(file_data)} bytes, {len(packet_list)} packets")
    return packet_list


def send_file(server_host: str, server_port: int, packet_list: list[bytes], window_size: int):
    """Transfer packets using Go-back-N protocol."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(TIMEOUT)
    server_address = (server_host, server_port)
    
    window_base = 0                    # oldest unACKed sequence number
    next_sequence_number = 0           # next sequence number to send
    timer_start_time = None            # when timer was started
    retransmission_count = 0
    
    print(f"Sending to {server_host}:{server_port}, window={window_size}")
    transfer_start_time = time.time()
    
    while window_base < len(packet_list):
        # Send packets within window
        while next_sequence_number < window_base + window_size and next_sequence_number < len(packet_list):
            client_socket.sendto(packet_list[next_sequence_number], server_address)
            if next_sequence_number == window_base:
                timer_start_time = time.time()
            next_sequence_number += 1
        
        # Wait for ACK
        try:
            ack_packet_data, _ = client_socket.recvfrom(HEADER_SIZE)
            parsed_ack = parse_packet(ack_packet_data)
            
            if parsed_ack and is_ack(parsed_ack[2]):
                acked_sequence_number = parsed_ack[0]
                if acked_sequence_number >= window_base:
                    window_base = acked_sequence_number + 1
                    timer_start_time = time.time() if window_base < next_sequence_number else None
        except socket.timeout:
            pass
        
        # Handle timeout: retransmit all unACKed packets
        if timer_start_time and (time.time() - timer_start_time) >= TIMEOUT:
            print(f"Timeout, sequence number = {window_base}")
            timer_start_time = time.time()
            for sequence_number in range(window_base, next_sequence_number):
                client_socket.sendto(packet_list[sequence_number], server_address)
                retransmission_count += 1
    
    total_transfer_time = time.time() - transfer_start_time
    print(f"\nDone! Time: {total_transfer_time:.3f}s, Retransmissions: {retransmission_count}")
    client_socket.close()
    return total_transfer_time


def main():
    if len(sys.argv) != 6:
        print("Usage: python client.py <host> <port> <file> <window-size> <mss>")
        sys.exit(1)
    
    server_host = sys.argv[1]
    server_port = int(sys.argv[2])
    input_filename = sys.argv[3]
    window_size = int(sys.argv[4])
    max_segment_size = int(sys.argv[5])
    
    packet_list = create_packets(input_filename, max_segment_size)
    if packet_list:
        send_file(server_host, server_port, packet_list, window_size)


if __name__ == "__main__":
    main()
