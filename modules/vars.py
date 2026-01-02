import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')
OWNER = int(os.getenv('OWNER', '0'))
CREDIT = os.getenv('CREDIT', 'Bot Owner')

AUTH_USERS = []
TOTAL_USERS = []
cookies_file_path = "youtube_cookies.txt"
api_url = ""
api_token = ""
