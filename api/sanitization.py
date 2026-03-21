"""Input sanitization utilities."""

import re
from pathlib import Path

# Allowed characters for file paths (simple whitelist)
ALLOWED_CHARS = re.compile(r'^[a-zA-Z0-9_\-\./\\ ]+$')

# Maximum file size (100MB)
MAX_FILE_SIZE = 100 * 1024 * 1024

def sanitize_file_path(file_path: str) -> str:
    """Sanitize file paths to prevent path traversal attacks."""
    # Normalize path
    normalized_path = str(Path(file_path).resolve())
    
    # Check for malicious patterns
    if '..' in normalized_path or '\\' in normalized_path or '/' in normalized_path:
        raise ValueError("Invalid file path - traversal attempts detected")
    
    # Check for allowed characters
    if not ALLOWED_CHARS.match(normalized_path):
        raise ValueError("Invalid file path - contains forbidden characters")
    
    return normalized_path

def validate_file_size(file_obj, max_size: int = MAX_FILE_SIZE) -> None:
    """Validate file size to prevent large uploads."""
    file_obj.seek(0, 2)  # Move to end of file
    size = file_obj.tell()
    file_obj.seek(0)  # Reset to beginning
    
    if size > max_size:
        raise ValueError(f"File size exceeds maximum limit of {max_size / (1024 * 1024)}MB")

def sanitize_string_input(input_str: str, max_length: int = 1000) -> str:
    """Sanitize string inputs to prevent injection attacks."""
    # Trim whitespace
    sanitized = input_str.strip()
    
    # Check length
    if len(sanitized) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length} characters")
    
    # Remove potentially malicious characters
    sanitized = re.sub(r'[<>&;`\'"]', '', sanitized)
    
    return sanitized
