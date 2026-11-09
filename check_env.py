"""Checks that your .env file is found and the key is loaded (never prints the key)."""
import os
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("GNANI_API_KEY")

if not key or key.startswith("paste-your"):
    print("Key loaded: False")
    print("-> Open .env and replace the placeholder with your real key.")
else:
    print("Key loaded: True | length:", len(key))
