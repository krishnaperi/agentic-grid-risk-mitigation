import os
import snowflake.connector
from dotenv import load_dotenv
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric import dsa
from cryptography.hazmat.primitives import serialization

# Load environment variables from .env file
load_dotenv()

def get_snowflake_connection():
    """
    Establish and return a Snowflake connection using environment variables and Key-Pair Authentication.
    """
    private_key_path = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
    if not private_key_path or not os.path.exists(private_key_path):
        raise ValueError(f"Private key file not found at {private_key_path}")

    # Read the private key
    with open(private_key_path, "rb") as key:
        p_key = serialization.load_pem_private_key(
            key.read(),
            password=os.environ.get('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE', '').encode() if os.environ.get('SNOWFLAKE_PRIVATE_KEY_PASSPHRASE') else None,
            backend=default_backend()
        )

    pkb = p_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    try:
        conn = snowflake.connector.connect(
            user=os.getenv("SNOWFLAKE_USERNAME"),
            account=os.getenv("SNOWFLAKE_ACCOUNT"),
            private_key=pkb,
            warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
            database=os.getenv("SNOWFLAKE_DATABASE") or None,
            schema=os.getenv("SNOWFLAKE_SCHEMA") or None,
            role=os.getenv("SNOWFLAKE_ROLE") or None
        )
        return conn
    except Exception as e:
        print(f"Error connecting to Snowflake: {e}")
        raise

if __name__ == "__main__":
    print("Testing Snowflake Connection...")
    try:
        conn = get_snowflake_connection()
        print("Successfully connected to Snowflake!")
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

