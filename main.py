import asyncio
import logging
import os

import aiosqlite
import emoji
import stoat
from dotenv import load_dotenv
from stoat.ext import commands

import config

# Create bot

bot = commands.Bot(command_prefix=config.PREFIX)


# ==== FUNCTIONS ====
# Inicialize SQLite database
async def init_db():
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


async def get_server(event):
    channel = bot.get_channel(event.channel_id)
    if channel is None:
        logger.error("Channel was not found in bot's caches")
        return

    if not hasattr(channel, "get_server"):
        logger.error("Reaction was added in DM")
        return

    get_server_func = getattr(channel, "get_server")
    server = get_server_func()

    if server is None:
        logger.error("Server was not found for this channel")
        return

    return server


def main():
    global logger
    # logger setup
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(config.LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    logger = logging.getLogger(__name__)

    # Load and initialize database file
    load_dotenv()

    # Load token
    token = os.getenv("BLOT_TOKEN")
    if token is None:
        logger.error("Unable to load token from eniroment variable BLOT_TOKEN")
        exit(1)

    bot.run(token)


# ==== COMMANDS ====
# On !ping command
@bot.command()
async def ping(context):
    try:
        await context.send("Pong!")
    except Exception as err:
        logger.error(f"Unable to print response to !ping: {err}")
    logger.info("Executed !ping command")


# On !help command
@bot.command()
async def help(context, command=""):
    if command == "":
        await context.send(
            "👽 Blot\n!help   Show this help\n!ping    Check if is bot online\n!createmsg  Create reaction role message\n!kick   Kick member from server\n!ban Ban Member from server\n!unban Unban User from server"
        )
    else:
        if command == "!help":
            await context.send("Just type !help")
        elif command == "!ping":
            await context.send("Just type !ping")
        elif command == "!createmsg":
            await context.send(
                '!createmsg <role-id> <emoji> "<message-text>" (!createmsg 123456789 ✅ "React to get role")'
            )
        elif command == "!kick":
            await context.send("!kick <ping> (!kick @Spammer)")
        elif command == "!ban":
            await context.send("!ban <ping> (!ban @Spammer)")
        elif command == "!unban":
            await context.send("!unban <username> (!unban @Spammer#1234)")
        else:
            await context.send("Invalid command")
    logger.info("Executed !help command")


# On !createmsg command
@bot.command()
@commands.has_server_permissions(manage_roles=True)
async def createmsg(context, role_id, raw_emoji="✅", msg_text: str = "Choose role"):
    formated_emoji = emoji.emojize(raw_emoji, language="alias")
    msg = await context.send(msg_text)

    try:
        await msg.react(formated_emoji)
    except Exception:
        logger.warning("Unable to react to message")

    try:
        server_id = context.server.id
        await db.execute(
            "INSERT INTO msg_roles (server_id, message_id, emoji, role_id) VALUES (?, ?, ?, ?)",
            (server_id, msg.id, formated_emoji, role_id),
        )
        await db.commit()
        logger.info("New message role was been saved to database")
    except Exception as err:
        logger.error(f"Unable to save message to database: {err}")
        return

    await context.send(f"Message Created! ID: `{msg.id}`")
    logger.info("Executed !createmsg command")


# On !kick
@bot.command()
@commands.has_server_permissions(kick_members=True)
async def kick(context, member: stoat.Member):
    try:
        await member.kick()
        await context.send(f"Member kicked!")
        logger.info("Executed !kick command")
    except Exception as e:
        logger.error(f"kick failed: {e}")
        await context.send(f"Failed to kick member: {e}")


# On !ban
@bot.command()
@commands.has_server_permissions(ban_members=True)
async def ban(context, member: stoat.Member, *, reason: str = "No reason provided"):
    try:
        await context.server.ban(member.id, reason=reason)
        await context.send(f"Member banned! Reason: {reason}")
        logger.info("Executed !ban command")
    except Exception as e:
        logger.error(f"ban failed: {e}")
        await context.send(f"Failed to ban member")


# On !unban
@bot.command()
@commands.has_server_permissions(ban_members=True)
async def unban(context, username: str):
    try:
        bans = await context.server.fetch_bans()
        ban = next(
            (b for b in bans if f"{b.user.name}#{b.user.discriminator}" == username),
            None,
        )
        if ban is None:
            await context.send(f"User `{username}` not found in ban list!")
            return
        await context.server.unban(ban.user.id)
        await context.send(f"User `{username}` unbanned!")
        logger.info("Executed !unban command")
    except Exception as e:
        logger.error(f"unban failed: {e}")
        await context.send(f"Failed to unban")



xp_ratio = 1.5
xp_first_level = 20

#on !level
@bot.command()
async def level(ctx):
    user_id = ctx.author.id
    async with db.execute("SELECT * FROM levels WHERE user_id=?", (user_id,)) as cursor:
        row = await cursor.fetchone()
        if(row == None):
            await ctx.channel.send(ctx.author.mention + " you dont have any level")
            return
        level = row[1]
        xp = row[2]
        max_xp_lvl = (xp_first_level * (xp_ratio ** level))
        await ctx.channel.send(ctx.author.mention + "you have Level " + str(level) + ",XP: " + str(xp) + "/" + str(max_xp_lvl))

#on !setlevelchannel <channel>
@bot.command()
@commands.has_permissions(manage_server=True)
async def setlevelchannel(ctx,channel):
    if channel == None:
        await ctx.channel.send("Invalid use of command")
        return

    channel = channel.strip('<#>')
    try:
        fetch = await bot.fetch_channel(channel)
    except:
        await ctx.channel.send("Must be valid channel on this server")
        return

    async with db.execute("SELECT * FROM level_channel WHERE server_id=?", (ctx.server.id,)) as cursor:
        row = await cursor.fetchone()
        if(row == None):
            await db.execute("INSERT INTO level_channel(server_id,channel_id)VALUES(?,?)",(ctx.server.id,ctx.channel.id))
        else:
            await db.execute("UPDATE level_channel SET channel_id=? WHERE server_id=?",(channel,ctx.server.id))
        await db.commit()



async def level_message(server_id,channel_id,message):
    async with db.execute("SELECT * FROM level_channel WHERE server_id=?", (server_id,)) as cursor:
        row = await cursor.fetchone()
        channel = None
        if(row == None):
            channel = bot.get_channel(channel_id)
        else:
             channel = await bot.fetch_channel(row[1])
        await channel.send(message)
    


# XP system
@bot.on(stoat.MessageCreateEvent)
async def on_message(event):
    message = event.message

    if message.author.id == bot.user.id:
        return  # ignore the bot itself
    if message.content.startswith('!'):
        return  # ignore leveling when it's a command

    user_id = message.author.id  # obtain user id
    xp = len(message.content) / 10  # calculate total xp
    if xp == 0:
        xp = 1

    # checking if data associated with user already exists
    async with db.execute("SELECT * FROM levels WHERE user_id=?", (user_id,)) as cursor:
        rows = await cursor.fetchall()

    if len(rows) == 0:
        # data for user does not exist, starting from level 1
        level = 1
        if xp > xp_first_level:
            level = 2
            xp_cache = xp
            while xp_cache > (xp_first_level * (xp_ratio ** level)):
                xp_cache -= (xp_first_level * (xp_ratio ** level))
                level += 1
            xp = xp_cache
            await db.execute(
                "INSERT INTO levels (user_id, user_level, user_xp) VALUES (?, ?, ?)",
                (user_id, level, xp)
            )
            await db.commit()
            await level_message(message.server.id,message.channel.id,f"Congrats! {message.author.mention}, you achieved level {level}!")
        else:
            await db.execute(
                "INSERT INTO levels (user_id, user_level, user_xp) VALUES (?, ?, ?)",
                (user_id, level, xp)
            )
            await db.commit()
    else:
        row = rows[0]
        level = row[1]
        xp = xp + row[2]
        xp_needed = xp_first_level * (xp_ratio ** level)

        if xp > xp_needed:
            xp_cache = xp
            while xp_cache > (xp_first_level * (xp_ratio ** level)):
                xp_cache -= (xp_first_level * (xp_ratio ** level))
                level += 1
            xp = xp_cache
            await db.execute(
                "UPDATE levels SET user_level=?, user_xp=? WHERE user_id=?",
                (level, xp, user_id)
            )
            await db.commit()
            await level_message(message.server.id,message.channel.id,f"Congrats! {message.author.mention}, you achieved level {level}!")
        else:
            await db.execute(
                "UPDATE levels SET user_xp=? WHERE user_id=?",
                (xp, user_id)
            )
            await db.commit()
    

# ==== ERROR HANDLERS ====
@createmsg.error  # type: ignore
async def createmsg_error(context, error):
    if isinstance(error, commands.MissingPermissions):
        await context.send(
            "You don't have permissions to run this command (Manage Roles)!"
        )


@kick.error  # type: ignore
async def kick_error(context, error):
    if isinstance(error, commands.MissingPermissions):
        await context.send(
            "You don't have permissions to run this command (Kick Members)!"
        )


@ban.error  # type: ignore
async def ban_error(context, error):
    if isinstance(error, commands.MissingPermissions):
        await context.send(
            "You don't have permissions to run this command (Ban Members)!"
        )


@unban.error  # type: ignore
async def unban_error(context, error):
    if isinstance(error, commands.MissingPermissions):
        await context.send(
            "You don't have permissions to run this command (Ban Members)!"
        )


# ==== EVENTS ====
# On bot start
@bot.on(stoat.ReadyEvent)
async def on_ready(event):
    global db
    db = await aiosqlite.connect(config.DB_FILE)
    await init_db()
    logger.info(f"bot is online as {bot.user}")


# On add reaction
@bot.on(stoat.MessageReactEvent)
async def on_reaction_add(event):
    logger.info("Registered reaction add")
    msg_id = event.message_id

    emoji = str(event.emoji)

    logger.info("Registered valid reaction add")

    channel = bot.get_channel(event.channel_id)
    if channel is None:
        logger.error("Channel was not found in bot's caches")
        return

    if not hasattr(channel, "get_server"):
        logger.error("Reaction was added in DM")
        return

    get_server_func = getattr(channel, "get_server")
    server = get_server_func()

    if server is None:
        logger.error("Server was not found for this channel")
        return

    try:
        cursor = await db.execute(
            "SELECT role_id FROM msg_roles WHERE server_id = ? AND message_id = ? AND emoji = ?",
            (server.id, msg_id, emoji),
        )
        row = await cursor.fetchone()
        if row is None:
            return
        role_id = row[0]
    except Exception as err:
        logger.error(f"Unable to read from database: {err}")
        return

    member = server.get_member(event.user_id)
    if member is None:
        try:
            logger.info("Member not in cache, fetching from API...")
            member = await server.fetch_member(event.user_id)
        except Exception as err:
            logger.error(f"Failed to fetch member from server: {err}")
            return

    current_roles = list(member.role_ids)
    if role_id not in current_roles:
        current_roles.append(role_id)
        await member.edit(roles=current_roles)  # type: ignore


# On remove reaction
@bot.listen(stoat.MessageUnreactEvent)
async def on_reaction_remove(event):
    logger.info("Registered reaction delete")
    msg_id = event.message_id

    emoji = str(event.emoji)
    server = event.get_server()

    try:
        cursor = await db.execute(
            "SELECT role_id FROM msg_roles WHERE server_id = ? AND message_id = ? AND emoji = ?",
            (server.id, msg_id, emoji),
        )
        row = await cursor.fetchone()
        if row is None:
            return
        role_id = row[0]
    except Exception as err:
        logger.error(f"Unable to read from database: {err}")
        return

    if not role_id:
        return

    logger.info("Registered valid reaction delete")

    server = event.get_server()

    member = server.get_member(event.user_id)
    if member is None:
        try:
            logger.info("ember not in cache, fetching from API...")
            member = await server.fetch_member(event.user_id)
        except Exception as err:
            logger.error(f"Failed to fetch member from server: {err}")
            return

    current_roles = list(member.role_ids)
    if role_id in current_roles:
        current_roles.remove(role_id)
        await member.edit(roles=current_roles)  # type: ignore


# On remove message
@bot.on(stoat.MessageDeleteEvent)
async def on_message_delete(event):
    msg_id = event.message_id

    await db.execute(
        "DELETE FROM msg_roles WHERE message_id = ?",
        (msg_id,),
    )
    await db.commit()
    logger.info(f"Message {msg_id} was deleted. Deleted from database.")


asyncio.run(main())
