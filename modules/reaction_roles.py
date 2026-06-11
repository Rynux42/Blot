"""
modules/reaction_roles.py
Reaction roles: !createmsg, pridanie/odobranie role pri reakcii, čistenie po mazaní správy.
"""

import emoji as emoji_lib
import stoat
from stoat.ext import commands

import modules.base as base
from modules.base import bot, get_server


def setup():
    """Zaregistruje všetky handlery tohto modulu. Volá main.py pri štarte."""

    @bot.command()
    @commands.has_server_permissions(manage_roles=True)
    async def createmsg(
        context, role_id, raw_emoji="✅", msg_text: str = "Choose role"
    ):
        formated_emoji = emoji_lib.emojize(raw_emoji, language="alias")
        msg = await context.send(msg_text)

        try:
            await msg.react(formated_emoji)
        except Exception:
            base.logger.warning("Unable to react to message")

        try:
            server_id = context.server.id
            await base.db.execute(
                "INSERT INTO msg_roles (server_id, message_id, emoji, role_id) VALUES (?, ?, ?, ?)",
                (server_id, msg.id, formated_emoji, role_id),
            )
            await base.db.commit()
            base.logger.info("New message role saved to database")
        except Exception as err:
            base.logger.error(f"Unable to save message to database: {err}")
            return

        await context.send(f"Message Created! ID: `{msg.id}`")
        base.logger.info("Executed !createmsg command")

    @createmsg.error
    async def createmsg_error(context, error):
        if isinstance(error, commands.MissingPermissions):
            await context.send(
                "You don't have permissions to run this command (Manage Roles)!"
            )

    @bot.on(stoat.MessageReactEvent)
    async def on_reaction_add(event):
        base.logger.info("Registered reaction add")
        msg_id = event.message_id
        emoji_str = str(event.emoji)

        server = await get_server(event)
        if server is None:
            return

        try:
            cursor = await base.db.execute(
                "SELECT role_id FROM msg_roles WHERE server_id = ? AND message_id = ? AND emoji = ?",
                (server.id, msg_id, emoji_str),
            )
            row = await cursor.fetchone()
            if row is None:
                return
            role_id = row[0]
        except Exception as err:
            base.logger.error(f"Unable to read from database: {err}")
            return

        member = server.get_member(event.user_id)
        if member is None:
            try:
                base.logger.info("Member not in cache, fetching from API...")
                member = await server.fetch_member(event.user_id)
            except Exception as err:
                base.logger.error(f"Failed to fetch member: {err}")
                return

        current_roles = list(member.role_ids)
        if role_id not in current_roles:
            current_roles.append(role_id)
            await member.edit(roles=current_roles)  # type: ignore
        base.logger.info("Registered valid reaction add")

    @bot.on(stoat.MessageUnreactEvent)
    async def on_reaction_remove(event):
        base.logger.info("Registered reaction delete")
        msg_id = event.message_id
        emoji_str = str(event.emoji)

        server = await get_server(event)
        if server is None:
            return

        try:
            cursor = await base.db.execute(
                "SELECT role_id FROM msg_roles WHERE server_id = ? AND message_id = ? AND emoji = ?",
                (server.id, msg_id, emoji_str),
            )
            row = await cursor.fetchone()
            if row is None:
                return
            role_id = row[0]
        except Exception as err:
            base.logger.error(f"Unable to read from database: {err}")
            return

        if not role_id:
            return

        member = server.get_member(event.user_id)
        if member is None:
            try:
                base.logger.info("Member not in cache, fetching from API...")
                member = await server.fetch_member(event.user_id)
            except Exception as err:
                base.logger.error(f"Failed to fetch member: {err}")
                return

        current_roles = list(member.role_ids)
        if role_id in current_roles:
            current_roles.remove(role_id)
            await member.edit(roles=current_roles)  # type: ignore
        base.logger.info("Registered valid reaction delete")

    @bot.on(stoat.MessageDeleteEvent)
    async def on_message_delete(event):
        msg_id = event.message_id
        await base.db.execute(
            "DELETE FROM msg_roles WHERE message_id = ?",
            (msg_id,),
        )
        await base.db.commit()
        base.logger.info(f"Message {msg_id} deleted — removed from database.")
