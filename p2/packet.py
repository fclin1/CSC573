"""
Packet utilities for Simple-FTP Go-back-N ARQ.

Data Packet: [seq_num: 4B] [checksum: 2B] [flags: 2B] [data: MSS bytes]
ACK Packet:  [seq_num: 4B] [zeros: 2B]    [flags: 2B]
"""

import struct

DATA_FLAG = 0x5555  # 0101010101010101
ACK_FLAG = 0xAAAA   # 1010101010101010
HEADER_SIZE = 8


def checksum(data):
    """Compute Internet checksum (RFC 1071)."""
    # Handle both Python 2 strings and Python 3 bytes
    if isinstance(data, str):
        data = bytearray(data)
    
    if len(data) % 2:
        if isinstance(data, bytearray):
            data.append(0)
        else:
            data += b'\x00'
    
    total = 0
    for i in range(0, len(data), 2):
        # Handle both bytes and bytearray
        byte1 = data[i] if isinstance(data[i], int) else ord(data[i])
        byte2 = data[i + 1] if isinstance(data[i + 1], int) else ord(data[i + 1])
        total += (byte1 << 8) + byte2
        total = (total & 0xFFFF) + (total >> 16)  # fold carry
    
    return ~total & 0xFFFF


def make_data_packet(sequence_number, data):
    """Create a data packet: header + payload."""
    header = struct.pack('!IHH', sequence_number, checksum(data), DATA_FLAG)
    return header + data


def make_ack_packet(sequence_number):
    """Create an ACK packet."""
    return struct.pack('!IHH', sequence_number, 0, ACK_FLAG)


def parse_packet(packet):
    """Parse any packet. Returns (sequence_number, checksum_or_zero, flags, data) or None."""
    if len(packet) < HEADER_SIZE:
        return None
    sequence_number, checksum_or_zero, flags = struct.unpack('!IHH', packet[:HEADER_SIZE])
    return sequence_number, checksum_or_zero, flags, packet[HEADER_SIZE:]


def is_valid_data(sequence_number, received_checksum, flags, data):
    """Check if parsed packet is valid data with correct checksum."""
    return flags == DATA_FLAG and received_checksum == checksum(data)


def is_ack(flags):
    """Check if flags indicate an ACK packet."""
    return flags == ACK_FLAG
