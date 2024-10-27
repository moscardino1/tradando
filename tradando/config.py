import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    HF_API_URL = "https://api-inference.huggingface.co/models/"
    HF_API_KEY = os.getenv('HF')
    INITIAL_CASH = 10000
