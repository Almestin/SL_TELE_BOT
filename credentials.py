from os import getenv
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN: str = getenv("BOT_TOKEN")
    OPENAI_TOKEN: str = getenv("OPENAI_TOKEN")

config = Config()
