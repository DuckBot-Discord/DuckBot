import logging
import os
import tekore as tk

# Async stuff seperate
from dotenv import load_dotenv

# Local imports always at bottom
from main import DuckBot

os.environ['JISHAKU_HIDE'] = 'True'

load_dotenv()

log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='[%(asctime)-15s] %(message)s')

token_spotify = tk.request_client_token(
    client_id=os.getenv('SPOTIFY_CLIENT_ID'),
    client_secret=os.getenv('SPOTIFY_CLIENT_SECRET'))

if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')

    bot = DuckBot()
    bot.spotify = tk.Spotify(token_spotify, asynchronous=True)
    bot.run(TOKEN, reconnect=True)
