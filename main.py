import logging
import os

import aiosqlite
import stoat
from dotenv import load_dotenv

import config
import modules.levels as levels
import modules.moderation as moderation
import modules.reaction_roles as reaction_roles
from modules.base import bot, set_db

# ==== LOGGING ====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger("blot")


# ==== DB INIT ====
async def init_db(db):
    try:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS msg_roles (
                server_id TEXT,
                message_id TEXT,
                emoji TEXT,
                role_id TEXT,
                PRIMARY KEY (server_id, message_id, emoji)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS levels (
                server_id, TEXT,
                user_id INT,
                user_level INT,
                user_xp BIGINT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS level_channel (
                server_id INT,
                channel_id INT
            )
        """)
        await db.commit()
        logger.info("Database initialized")
    except Exception as err:
        logger.error(f"Failed to initialize database: {err}")
        exit(1)


# ==== COMMANDS ====
@bot.command()
async def ping(context):
    try:
        await context.send("Pong!")
    except Exception as err:
        logger.error(f"Unable to respond to !ping: {err}")
    logger.info("Executed !ping command")


@bot.command()
async def help(context, command=""):
    lines = {
        "": (
            "👽 Blot\n"
            "!help                          Show this help\n"
            "!ping                          Check if bot is online\n"
            "!createmsg <role> <emoji> <msg> Create reaction role message\n"
            "!kick <member>                 Kick a member\n"
            "!ban <member> [reason]         Ban a member\n"
            "!unban <username#tag>          Unban a user\n"
            "!level                         Show your level\n"
            "!setlevelchannel <#channel>    Set level-up announcement channel"
            "!top                           Show list of best members"
        ),
        "!help": "Just type !help",
        "!ping": "Just type !ping",
        "!createmsg": '!createmsg <role-id> <emoji> "<text>"  —  e.g. !createmsg 123456 ✅ "React to get role"',
        "!kick": "!kick <@member>  —  e.g. !kick @Spammer",
        "!ban": "!ban <@member> [reason]  —  e.g. !ban @Spammer rule violation",
        "!unban": "!unban <username#tag>  —  e.g. !unban Spammer#1234",
        "!level": "!level (Show your level) / !level @Spammer (Show level of other member)",
        "!setlevelchannel": "!setlevelchannel <#channel>  —  e.g. !setlevelchannel #general / !setlevelchannel (Choose channel where you are)",
        "!top": "Just type !top",
    }
    await context.send(lines.get(command, "Unknown command"))
    logger.info("Executed !help command")


# ==== EVENTS ====
@bot.on(stoat.ReadyEvent)
async def on_ready(event):
    db = await aiosqlite.connect(config.DB_FILE)
    set_db(db)
    await init_db(db)
    logger.info(f"Bot is online as {bot.user}")


# ==== LOAD MODULES ====
reaction_roles.setup()
moderation.setup()
levels.setup()


# ==== START ====
def main():
    load_dotenv()
    token = os.getenv("BLOT_TOKEN")
    if token is None:
        logger.error("Unable to load token from environment variable BLOT_TOKEN")
        exit(1)
    bot.run(token)


main()
