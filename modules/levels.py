"""
modules/levels.py
Level/XP systém: !level, !setlevelchannel, automatické XP za správy.
"""

import math

import aiohttp
import stoat
from stoat.ext import commands

import config
import modules.base as base
from modules import imggen
from modules.base import bot

XP_RATIO = config.XP_RATIO
XP_FIRST_LEVEL = config.XP_FIRST_LEVEL

CDNClient = stoat.CDNClient(state=bot.state)


async def _level_message(server_id: int, channel_id: int, message: str):
    """Pošle level-up správu do nastaveného kanálu, alebo do pôvodného kanálu."""
    async with base.db.execute(
        "SELECT channel_id FROM level_channel WHERE server_id=?", (server_id,)
    ) as cursor:
        row = await cursor.fetchone()

    if row is None:
        channel = base.bot.get_channel(channel_id)
    else:
        channel = await base.bot.fetch_channel(row[0])

    if channel is not None:
        await channel.send(message)


def _calc_level_up(current_level: int, xp: float):
    """
    Vypočíta nový level a zvyšné XP po level-upe.
    Vracia (new_level, remaining_xp).
    """
    level = current_level
    while xp > (XP_FIRST_LEVEL * (XP_RATIO**level)):
        xp -= XP_FIRST_LEVEL * (XP_RATIO**level)
        level += 1
    return level, xp


def setup():
    """Zaregistruje všetky handlery tohto modulu. Volá main.py pri štarte."""


@bot.command()
async def top(ctx):
    server_id = ctx.server.id
    author_id = ctx.author.id

    async with base.db.execute(
        "SELECT user_id, user_level, user_xp FROM levels WHERE server_id=? ORDER BY user_level DESC, user_xp DESC",
        (server_id,),
    ) as cursor:
        rows = await cursor.fetchall()

    if not rows:
        await ctx.channel.send("No levels yet on this server!")
        return

    author_rank = None
    for i, row in enumerate(rows, 1):
        if row[0] == author_id:
            author_rank = i
            author_row = row
            break

    top10 = rows[:10]

    async def format_row(i, row):
        uid, lvl, xp = row
        try:
            user = await bot.fetch_user(uid)
            name = user.name
        except Exception:
            name = f"Unknown ({uid})"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"#{i}")
        return f"{medal} {name} — Level {lvl} ({math.floor(xp)} XP)"

    lines = []
    for i, row in enumerate(top10, 1):
        lines.append(await format_row(i, row))

    if author_rank is not None and author_rank > 10:
        lines.append("...")
        lines.append(f"#{author_rank} " + await format_row(author_rank, author_row))

    await ctx.channel.send("🏆 **Top 10**\n" + "\n".join(lines))
    base.logger.info("Executed !top command")

    @bot.command()
    async def level(ctx, user=""):
        server_id = ctx.server.id
        if not user:
            user_id = ctx.author.id
        else:
            user_id = user.strip("<@>")

        async with base.db.execute(
            "SELECT user_level, user_xp FROM levels WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            await ctx.channel.send(ctx.author.mention + " you don't have any level yet")
            return

        user_level, xp = row[0], row[1]
        max_xp = XP_FIRST_LEVEL * (XP_RATIO**user_level)

        if ctx.author.avatar.url() is None:
            img = imggen.generateImage(
                None, user_level, math.floor(xp), math.floor(max_xp), ctx.author.name
            )
        else:
            img = imggen.generateImage(
                ctx.author.avatar.url(),
                user_level,
                math.floor(xp),
                math.floor(max_xp),
                ctx.author.name,
            )

        form = aiohttp.FormData()
        form.add_field("file", img, filename="level_card.png", content_type="image/png")
        url = await CDNClient.upload("attachments", form)

        await ctx.channel.send(content="", attachments=[url])

    @bot.command()
    @commands.has_server_permissions(manage_server=True)
    async def setlevelchannel(ctx, channel: str = ""):
        if not channel:
            channel_id = ctx.channel.id
        else:
            channel_id = channel.strip("<#>")

        try:
            await bot.fetch_channel(channel_id)
        except Exception:
            await ctx.channel.send("Must be a valid channel on this server")
            return

        async with base.db.execute(
            "SELECT channel_id FROM level_channel WHERE server_id=?", (ctx.server.id,)
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            await base.db.execute(
                "INSERT INTO level_channel (server_id, channel_id) VALUES (?, ?)",
                (ctx.server.id, channel_id),
            )
        else:
            await base.db.execute(
                "UPDATE level_channel SET channel_id=? WHERE server_id=?",
                (channel_id, ctx.server.id),
            )
        await base.db.commit()
        await ctx.channel.send(f"Level-up channel set to <#{channel_id}>")
        base.logger.info("Executed !setlevelchannel command")

    # Error handler for !setlevelchannel
    @setlevelchannel.error
    async def setlevelchannel_error(context, error):
        if isinstance(error, commands.MissingPermissions):
            await context.send(
                "You don't have permissions to run this command (Manage server)!"
            )
            base.logger.info(
                "Missing permissions for !setlevelchannel command (Manage server)"
            )

    @bot.on(stoat.MessageCreateEvent)
    async def on_message(event):
        message = event.message
        server_id = event.message.server.id

        if message.author.id == bot.user.id:
            return
        if message.content.startswith("!"):
            return

        user_id = message.author.id
        gained_xp = max(1.0, len(message.content) / 10)

        async with base.db.execute(
            "SELECT user_level, user_xp FROM levels WHERE user_id=? AND server_id=?",
            (
                user_id,
                server_id,
            ),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            user_level, xp = 1, gained_xp
            leveled_up = False

            if xp > XP_FIRST_LEVEL:
                user_level = 2
                user_level, xp = _calc_level_up(user_level, xp)
                leveled_up = True

            await base.db.execute(
                "INSERT INTO levels (server_id, user_id, user_level, user_xp) VALUES (?, ?, ?, ?)",
                (server_id, user_id, user_level, xp),
            )
            await base.db.commit()

            if leveled_up:
                await _level_message(
                    message.server.id,
                    message.channel.id,
                    f"Congrats! {message.author.mention}, you achieved level {user_level}!",
                )
        else:
            user_level = row[0]
            xp = row[1] + gained_xp
            xp_needed = XP_FIRST_LEVEL * (XP_RATIO**user_level)

            if xp > xp_needed:
                user_level, xp = _calc_level_up(user_level, xp)
                await base.db.execute(
                    "UPDATE levels SET user_level=?, user_xp=? WHERE user_id=? AND server_id=?",
                    (user_level, xp, user_id, server_id),
                )
                await base.db.commit()
                await _level_message(
                    message.server.id,
                    message.channel.id,
                    f"Congrats! {message.author.mention}, you achieved level {user_level}!",
                )
            else:
                await base.db.execute(
                    "UPDATE levels SET user_xp=? WHERE user_id=? AND server_id=?",
                    (xp, user_id, server_id),
                )
                await base.db.commit()
