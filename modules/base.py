"""
modules/base.py
Zdieľaný stav pre všetky moduly: bot, db, logger a pomocné funkcie.
"""

import logging

from stoat.ext import commands

import config
import stoat

# Centrálne inštancie — moduly ich importujú priamo
bot = commands.Bot(command_prefix=config.PREFIX)
db = None  # nastavuje sa v on_ready (main.py) cez set_db()
logger = logging.getLogger("blot")




def set_db(connection):
    """Zavolá main.py po pripojení k DB, aby všetky moduly mali referenciu."""
    global db
    db = connection


async def get_server(event):
    """Získa server z eventu cez channel cache."""
    channel = bot.get_channel(event.channel_id)
    if channel is None:
        logger.error("Channel was not found in bot's caches")
        return None

    if not hasattr(channel, "get_server"):
        logger.error("Reaction was added in DM")
        return None

    server = channel.get_server()
    if server is None:
        logger.error("Server was not found for this channel")
        return None

    return server
