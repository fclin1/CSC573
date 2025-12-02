# Protocol message formatting and parsing for P2P-CI

import platform
from datetime import datetime
from config import VERSION, STATUS_CODES

CRLF = "\r\n"

def get_os_info():
    return f"{platform.system()} {platform.release()}"

def get_date_string():
    return datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")


# --- P2S Protocol (Peer-to-Server) ---

def build_add_request(rfc_number, hostname, port, title):
    return (
        f"ADD RFC {rfc_number} {VERSION}{CRLF}"
        f"Host: {hostname}{CRLF}"
        f"Port: {port}{CRLF}"
        f"Title: {title}{CRLF}"
        f"{CRLF}"
    )

def build_lookup_request(rfc_number, hostname, port, title):
    return (
        f"LOOKUP RFC {rfc_number} {VERSION}{CRLF}"
        f"Host: {hostname}{CRLF}"
        f"Port: {port}{CRLF}"
        f"Title: {title}{CRLF}"
        f"{CRLF}"
    )

def build_list_request(hostname, port):
    return (
        f"LIST ALL {VERSION}{CRLF}"
        f"Host: {hostname}{CRLF}"
        f"Port: {port}{CRLF}"
        f"{CRLF}"
    )

def build_p2s_response(status_code, data_lines=None):
    phrase = STATUS_CODES.get(status_code, "Unknown")
    response = f"{VERSION} {status_code} {phrase}{CRLF}{CRLF}"
    if data_lines:
        for line in data_lines:
            response += f"{line}{CRLF}"
    return response

def parse_p2s_request(message):
    """Parse P2S request. Returns dict with method, rfc_number, version, headers."""
    lines = message.strip().split(CRLF)
    if not lines:
        return None
    
    first_line = lines[0].split()
    if len(first_line) < 3:
        return None
    
    method = first_line[0]
    version = first_line[-1]
    
    # LIST ALL vs ADD/LOOKUP RFC <number>
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
    """Parse P2S response. Returns dict with version, status_code, phrase, data_lines."""
    lines = message.strip().split(CRLF)
    if not lines:
        return None
    
    first_line = lines[0].split(None, 2)
    if len(first_line) < 3:
        return None
    
    try:
        status_code = int(first_line[1])
    except ValueError:
        return None
    
    # Find data after empty line
    data_lines = []
    found_sep = False
    for line in lines[1:]:
        if not found_sep:
            if line == "":
                found_sep = True
        elif line:
            data_lines.append(line)
    
    return {
        "version": first_line[0],
        "status_code": status_code,
        "phrase": first_line[2],
        "data_lines": data_lines
    }


# --- P2P Protocol (Peer-to-Peer) ---

def build_get_request(rfc_number, hostname, os_info=None):
    if os_info is None:
        os_info = get_os_info()
    return (
        f"GET RFC {rfc_number} {VERSION}{CRLF}"
        f"Host: {hostname}{CRLF}"
        f"OS: {os_info}{CRLF}"
        f"{CRLF}"
    )

def build_get_response(status_code, data=None, last_modified=None):
    phrase = STATUS_CODES.get(status_code, "Unknown")
    os_info = get_os_info()
    date_str = get_date_string()
    
    if status_code == 200 and data is not None:
        content_length = len(data.encode('utf-8'))
        return (
            f"{VERSION} {status_code} {phrase}{CRLF}"
            f"Date: {date_str}{CRLF}"
            f"OS: {os_info}{CRLF}"
            f"Last-Modified: {last_modified or date_str}{CRLF}"
            f"Content-Length: {content_length}{CRLF}"
            f"Content-Type: text/plain{CRLF}"
            f"{CRLF}"
            f"{data}"
        )
    return (
        f"{VERSION} {status_code} {phrase}{CRLF}"
        f"Date: {date_str}{CRLF}"
        f"OS: {os_info}{CRLF}"
        f"{CRLF}"
    )

def parse_p2p_request(message):
    """Parse P2P GET request."""
    lines = message.strip().split(CRLF)
    if not lines:
        return None
    
    first_line = lines[0].split()
    if len(first_line) < 4 or first_line[0] != "GET" or first_line[1] != "RFC":
        return None
    
    try:
        rfc_number = int(first_line[2])
    except ValueError:
        return None
    
    headers = {}
    for line in lines[1:]:
        if not line:
            break
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key] = value
    
    return {
        "method": "GET",
        "rfc_number": rfc_number,
        "version": first_line[3],
        "headers": headers
    }

def parse_p2p_response(message):
    """Parse P2P GET response."""
    parts = message.split(CRLF + CRLF, 1)
    header_section = parts[0]
    data = parts[1] if len(parts) > 1 else ""
    
    lines = header_section.split(CRLF)
    if not lines:
        return None
    
    first_line = lines[0].split(None, 2)
    if len(first_line) < 3:
        return None
    
    try:
        status_code = int(first_line[1])
    except ValueError:
        return None
    
    headers = {}
    for line in lines[1:]:
        if ": " in line:
            key, value = line.split(": ", 1)
            headers[key] = value
    
    return {
        "version": first_line[0],
        "status_code": status_code,
        "phrase": first_line[2],
        "headers": headers,
        "data": data
    }
