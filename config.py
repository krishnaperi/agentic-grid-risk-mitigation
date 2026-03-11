import os
import snowflake.connector
from dotenv import load_dotenv
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from groq import Groq

# Load environment variables from .env file
load_dotenv()

def get_snowflake_connection():
    """
    Establish and return a Snowflake connection robustly for local and Railway.
    """
    # 1. Try to get the private key from environment variable (Railway style)
    raw_key = os.getenv('SNOWFLAKE_PRIVATE_KEY')
    p_key_bytes = None

    if raw_key:
        print("Using SNOWFLAKE_PRIVATE_KEY from environment...")
        formatted_key = raw_key.replace("\\n", "\n")
        p_key_bytes = formatted_key.encode()
    else:
        # 2. Try to get it from a file path (Local development style)
        private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
        if private_key_path and os.path.exists(private_key_path):
            print(f"Using Snowflake private key from file: {private_key_path}")
            with open(private_key_path, "rb") as key:
                p_key_bytes = key.read()
    
    if not p_key_bytes:
        raise ValueError("Snowflake private key not found in SNOWFLAKE_PRIVATE_KEY or SNOWFLAKE_PRIVATE_KEY_PATH")

    # Load the private key
    passphrase = os.getenv('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE')
    p_key = serialization.load_pem_private_key(
        p_key_bytes,
        password=passphrase.encode() if passphrase else None,
        backend=default_backend()
    )

    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    try:
        conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USER") or os.getenv("SNOWFLAKE_USERNAME"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            private_key=pkb,
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE"),
            schema=os.getenv("SNOWFLAKE_SCHEMA"),
            role=os.getenv("SNOWFLAKE_ROLE", "PUBLIC")
        )
        return conn
    except Exception as e:
        print(f"Error connecting to Snowflake: {e}")
        raise

def get_groq_client():
    """
    Initialize and return a Groq client.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is missing!")
    return Groq(api_key=api_key)

if __name__ == "__main__":
    print("Testing Integrations...")
    try:
        conn = get_snowflake_connection()
        print("Successfully connected to Snowflake!")
        conn.close()
    except Exception as e:
        print(f"Snowflake connection failed: {e}")

    try:
        client = get_groq_client()
        print("Groq client initialized successfully!")
    except Exception as e:
        print(f"Groq initialization failed: {e}")

