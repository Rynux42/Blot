"""
modules/moderation.py
Moderačné príkazy: !kick, !ban, !unban
"""

import stoat
from stoat.ext import commands

import modules.base as base
from modules.base import bot


def setup():
    """Zaregistruje všetky handlery tohto modulu. Volá main.py pri štarte."""

    @bot.command()
    @commands.has_server_permissions(kick_members=True)
    async def kick(context, member: stoat.Member):
        try:
            await member.kick()
            await context.send("Member kicked!")
            base.logger.info("Executed !kick command")
        except Exception as e:
            base.logger.error(f"kick failed: {e}")
            await context.send(f"Failed to kick member: {e}")

    @kick.error
    async def kick_error(context, error):
        if isinstance(error, commands.MissingPermissions):
            await context.send(
                "You don't have permissions to run this command (Kick Members)!"
            )

    @bot.command()
    @commands.has_server_permissions(ban_members=True)
    async def ban(context, member: stoat.Member, *, reason: str = "No reason provided"):
        try:
            await context.server.ban(member.id, reason=reason)
            await context.send(f"Member banned! Reason: {reason}")
            base.logger.info("Executed !ban command")
        except Exception as e:
            base.logger.error(f"ban failed: {e}")
            await context.send("Failed to ban member")

    @ban.error
    async def ban_error(context, error):
        if isinstance(error, commands.MissingPermissions):
            await context.send(
                "You don't have permissions to run this command (Ban Members)!"
            )

    @bot.command()
    @commands.has_server_permissions(ban_members=True)
    async def unban(context, username: str):
        try:
            bans = await context.server.fetch_bans()
            entry = next(
                (
                    b
                    for b in bans
                    if f"{b.user.name}#{b.user.discriminator}" == username
                ),
                None,
            )
            if entry is None:
                await context.send(f"User `{username}` not found in ban list!")
                return
            await context.server.unban(entry.user.id)
            await context.send(f"User `{username}` unbanned!")
            base.logger.info("Executed !unban command")
        except Exception as e:
            base.logger.error(f"unban failed: {e}")
            await context.send("Failed to unban")

    @unban.error
    async def unban_error(context, error):
        if isinstance(error, commands.MissingPermissions):
            await context.send(
                "You don't have permissions to run this command (Ban Members)!"
            )
