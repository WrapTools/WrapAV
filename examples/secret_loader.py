from pathlib import Path
import sys

def load_secret(secret_key, env_file=".env"):
    """
    Loads a secret value from a .env file.

    :param env_file: Path to the .env file (defaults to ".env")
    :param secret_key: The key of the secret to retrieve
    :return: The secret value as a string, or None if the key does not exist
    """
    # Determine the directory where the script is executed (whether it's PyCharm or PyInstaller)
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller executable
        env_file_path = Path(sys.executable).parent / env_file
    else:
        # Running in PyCharm or directly from source, resolve from the current working directory
        env_file_path = Path.cwd() / env_file

    print(f"Looking for .env file at: {env_file_path}")  # Debugging line

    secrets = {}

    # Check if the .env file exists at the calculated path
    if not env_file_path.exists():
        print(f"Warning: {env_file_path} not found.")
        # You can choose to raise an error here or handle it differently
        # raise FileNotFoundError(f"{env_file_path} not found.")

    # Load secrets from the .env file if it exists
    if env_file_path.exists():
        with open(env_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines or comments
                if not line or line.startswith('#'):
                    continue
                # Key-Value pairs are assumed to be 'key=value'
                if '=' in line:
                    key, value = line.split('=', 1)
                    secrets[key.strip()] = value.strip()

    # Return the value of the secret if it exists
    return secrets.get(secret_key)
