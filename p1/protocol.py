"""
Protocol message formatting and parsing for P2P-CI system.
Handles both P2P (peer-to-peer) and P2S (peer-to-server) protocols.
"""

import platform
from datetime import datetime
from config import VERSION, STATUS_CODES

# Line endings
CRLF = "\r\n"


def get_os_info():
    """Get OS information string."""
    return f"{platform.system()} {platform.release()}"


def get_date_string():
    """Get current date in HTTP format."""
    return datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")


# =============================================================================
# P2S Protocol (Peer-to-Server)
# =============================================================================

def build_add_request(rfc_number, hostname, port, title):
    """
    Build an ADD request message.
    
    ADD RFC <number> P2P-CI/1.0
    Host: <hostname>
    Port: <port>
    Title: <title>
    """
    return (
        f"ADD RFC {rfc_number} {VERSION}{CRLF}"
        f"Host: {hostname}{CRLF}"
        f"Port: {port}{CRLF}"
        f"Title: {title}{CRLF}"
        f"{CRLF}"
    )


def build_lookup_request(rfc_number, hostname, port, title):
    """
    Build a LOOKUP request message.
    
    LOOKUP RFC <number> P2P-CI/1.0
    Host: <hostname>
    Port: <port>
    Title: <title>
    """
    return (
        f"LOOKUP RFC {rfc_number} {VERSION}{CRLF}"
        f"Host: {hostname}{CRLF}"
        f"Port: {port}{CRLF}"
        f"Title: {title}{CRLF}"
        f"{CRLF}"
    )


def build_list_request(hostname, port):
    """
    Build a LIST request message.
    
    LIST ALL P2P-CI/1.0
    Host: <hostname>
    Port: <port>
    """
    return (
        f"LIST ALL {VERSION}{CRLF}"
        f"Host: {hostname}{CRLF}"
        f"Port: {port}{CRLF}"
        f"{CRLF}"
    )


def build_p2s_response(status_code, data_lines=None):
    """
    Build a P2S response message.
    
    P2P-CI/1.0 <status_code> <phrase>
    
    <data lines>
    """
    phrase = STATUS_CODES.get(status_code, "Unknown")
    response = f"{VERSION} {status_code} {phrase}{CRLF}{CRLF}"
    
    if data_lines:
        for line in data_lines:
            response += f"{line}{CRLF}"
    
    return response


def parse_p2s_request(message):
    """
    Parse a P2S request message.
    
    Returns dict with: method, rfc_number (or 'ALL'), version, headers
    """
    lines = message.strip().split(CRLF)
    if not lines:
        return None
    
    # Parse first line: METHOD RFC/ALL <number/ALL> VERSION
    first_line = lines[0].split()
    if len(first_line) < 3:
        return None
    
    method = first_line[0]
    version = first_line[-1]
    
    # Handle LIST ALL vs ADD/LOOKUP RFC <number>
    if method == "LIST":
        rfc_number = "ALL"
    else:
        if len(first_line) < 4 or first_line[1] != "RFC":
            return None
        try:
            rfc_number = int(first_line[2])
        except ValueError:
            return None
    
    # Parse headers
    headers = {}
    for line in lines[1:]:
        if not line:
            break
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key] = value
    
    return {
        "method": method,
        "rfc_number": rfc_number,
        "version": version,
        "headers": headers
    }


def parse_p2s_response(message):
    """
    Parse a P2S response message.
    
    Returns dict with: version, status_code, phrase, data_lines
    """
    lines = message.strip().split(CRLF)
    if not lines:
        return None
    
    # Parse first line: VERSION STATUS_CODE PHRASE
    first_line = lines[0].split(None, 2)
    if len(first_line) < 3:
        return None
    
    version = first_line[0]
    try:
        status_code = int(first_line[1])
    except ValueError:
        return None
    phrase = first_line[2]
    
    # Find empty line separator and get data lines
    data_lines = []
    found_separator = False
    for line in lines[1:]:
        if not found_separator:
            if line == "":
                found_separator = True
        else:
            if line:
                data_lines.append(line)
    
    return {
        "version": version,
        "status_code": status_code,
        "phrase": phrase,
        "data_lines": data_lines
    }


# =============================================================================
# P2P Protocol (Peer-to-Peer file transfer)
# =============================================================================

def build_get_request(rfc_number, hostname, os_info=None):
    """
    Build a GET request message for RFC download.
    
    GET RFC <number> P2P-CI/1.0
    Host: <hostname>
    OS: <os_info>
    """
    if os_info is None:
        os_info = get_os_info()
    
    return (
        f"GET RFC {rfc_number} {VERSION}{CRLF}"
        f"Host: {hostname}{CRLF}"
        f"OS: {os_info}{CRLF}"
        f"{CRLF}"
    )


def build_get_response(status_code, data=None, last_modified=None):
    """
    Build a GET response message.
    
    P2P-CI/1.0 <status_code> <phrase>
    Date: <date>
    OS: <os>
    Last-Modified: <date>
    Content-Length: <length>
    Content-Type: text/text
    
    <data>
    """
    phrase = STATUS_CODES.get(status_code, "Unknown")
    os_info = get_os_info()
    date_str = get_date_string()
    
    if status_code == 200 and data is not None:
        content_length = len(data.encode('utf-8'))
        if last_modified is None:
            last_modified = date_str
        
        response = (
            f"{VERSION} {status_code} {phrase}{CRLF}"
            f"Date: {date_str}{CRLF}"
            f"OS: {os_info}{CRLF}"
            f"Last-Modified: {last_modified}{CRLF}"
            f"Content-Length: {content_length}{CRLF}"
            f"Content-Type: text/plain{CRLF}"
            f"{CRLF}"
            f"{data}"
        )
    else:
        response = (
            f"{VERSION} {status_code} {phrase}{CRLF}"
            f"Date: {date_str}{CRLF}"
            f"OS: {os_info}{CRLF}"
            f"{CRLF}"
        )
    
    return response


def parse_p2p_request(message):
    """
    Parse a P2P GET request message.
    
    Returns dict with: method, rfc_number, version, headers
    """
    lines = message.strip().split(CRLF)
    if not lines:
        return None
    
    # Parse first line: GET RFC <number> VERSION
    first_line = lines[0].split()
    if len(first_line) < 4:
        return None
    
    method = first_line[0]
    if method != "GET" or first_line[1] != "RFC":
        return None
    
    try:
        rfc_number = int(first_line[2])
    except ValueError:
        return None
    
    version = first_line[3]
    
    # Parse headers
    headers = {}
    for line in lines[1:]:
        if not line:
            break
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key] = value
    
    return {
        "method": method,
        "rfc_number": rfc_number,
        "version": version,
        "headers": headers
    }


def parse_p2p_response(message):
    """
    Parse a P2P GET response message.
    
    Returns dict with: version, status_code, phrase, headers, data
    """
    # Split headers and data at double CRLF
    parts = message.split(CRLF + CRLF, 1)
    header_section = parts[0]
    data = parts[1] if len(parts) > 1 else ""
    
    lines = header_section.split(CRLF)
    if not lines:
        return None
    
    # Parse first line: VERSION STATUS_CODE PHRASE
    first_line = lines[0].split(None, 2)
    if len(first_line) < 3:
        return None
    
    version = first_line[0]
    try:
        status_code = int(first_line[1])
    except ValueError:
        return None
    phrase = first_line[2]
    
    # Parse headers
    headers = {}
    for line in lines[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key] = value
    
    return {
        "version": version,
        "status_code": status_code,
        "phrase": phrase,
        "headers": headers,
        "data": data
    }
