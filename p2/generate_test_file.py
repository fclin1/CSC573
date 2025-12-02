"""Generate a 1MB test file for Simple-FTP transfer testing."""
import random
import string
import os

filename = "test_1mb.txt"
size = 1024 * 1024  # 1 MB

# Generate random readable text (letters, digits, spaces, newlines)
chars = string.ascii_letters + string.digits + " " * 10 + "\n" * 2
content = "".join(random.choice(chars) for _ in range(size))

with open(filename, "w") as f:
    f.write(content)

print(f"Created {filename}: {os.path.getsize(filename):,} bytes")
