"""
Utility to load AWS credentials from external file
"""

import os


def load_credentials_from_file(filepath='aws_credentials.txt'):
    """
    Load AWS credentials from a text file and set as environment variables.
    
    File format:
        AWS_BEARER_TOKEN_BEDROCK=your_token_here
        AWS_DEFAULT_REGION=us-east-1
    
    Lines starting with # are ignored (comments).
    Empty lines are ignored.
    
    Args:
        filepath (str): Path to credentials file. Default is 'aws_credentials.txt'
    
    Returns:
        dict: Dictionary of loaded credentials
    
    Raises:
        FileNotFoundError: If credentials file doesn't exist
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(
            f"Credentials file not found: {filepath}\n"
            f"Please create the file with your AWS credentials."
        )
    
    credentials = {}
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            
            # Skip comments and empty lines
            if not line or line.startswith('#'):
                continue
            
            # Parse KEY=VALUE format
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Set as environment variable
                os.environ[key] = value
                credentials[key] = value
    
    return credentials


def verify_credentials():
    """
    Verify that required AWS credentials are set.
    
    Returns:
        bool: True if all required credentials are present
    """
    required = ['AWS_BEARER_TOKEN_BEDROCK', 'AWS_DEFAULT_REGION']
    missing = []
    
    for key in required:
        if key not in os.environ:
            missing.append(key)
    
    if missing:
        print(f"✗ Missing credentials: {', '.join(missing)}")
        return False
    
    print("✓ All required credentials are set")
    print(f"  Region: {os.environ.get('AWS_DEFAULT_REGION')}")
    print(f"  Token: {os.environ.get('AWS_BEARER_TOKEN_BEDROCK')[:20]}...")
    return True


if __name__ == "__main__":
    # Test loading credentials
    try:
        creds = load_credentials_from_file()
        print(f"✓ Loaded {len(creds)} credentials from file")
        verify_credentials()
    except FileNotFoundError as e:
        print(f"✗ Error: {e}")
