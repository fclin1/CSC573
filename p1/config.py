"""
Configuration constants for P2P-CI system.
"""

# Server configuration
SERVER_PORT = 7734

# Protocol version
VERSION = "P2P-CI/1.0"

# Status codes and phrases
STATUS_CODES = {
    200: "OK",
    400: "Bad Request",
    404: "Not Found",
    505: "P2P-CI Version Not Supported"
}

# Methods
P2S_METHODS = ["ADD", "LOOKUP", "LIST"]
P2P_METHODS = ["GET"]

# RFC storage directory
RFC_DIR = "rfc"
