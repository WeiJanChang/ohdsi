from dotenv import load_dotenv # dotenv: reads key-value pairs from a .env file
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

print("API key loaded:", api_key is not None)