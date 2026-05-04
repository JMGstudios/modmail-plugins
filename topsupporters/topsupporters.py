# Plugin to retrieve every staff member that has been participating in the modmail thread, and list them in order in the final close embed.

from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any, Dict, Tuple

import discord
from discord.ext import commands

from core.models import getLogger

logger = getLogger(__name__)

logger.setLevel(logging.ERROR)


class TopSupporters(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("[TopSupporters] Plugin initialized.")

    def _format_counter(self, counter: Counter, guild: discord.Guild, empty_text: str) -> str:
        if not counter:
            return empty_text

        lines = []
        for position, (user_id, amount) in enumerate(counter.most_common(), start=1):
            member = guild.get_member(user_id) if guild else None
            display = member.mention if member else f"<@{user_id}>"
            lines.append(f"`#{position}` {display} → `{amount}` messages")

        return "\n".join(lines)[:1024]

    def _extract_author(self, message: Dict[str, Any]) -> Dict[str, Any]:
        author = message.get("author")
        if isinstance(author, dict):
            return author

        user = message.get("user")
        if isinstance(user, dict):
            return user

        creator = message.get("creator")
        if isinstance(creator, dict):
            return creator

        return {}

    def _count_from_log(self, thread_log: Dict[str, Any]) -> Tuple[Counter, Counter]:
        
        """Returns:
            user_interactions: staff messages sent to the user
            staff_discussions: internal messages"""
            
        user_interactions = Counter()
        staff_discussions = Counter()

        messages = thread_log.get("messages", [])
        if not isinstance(messages, list):
            return user_interactions, staff_discussions

        for message in messages:
            if not isinstance(message, dict):
                continue

            author = self._extract_author(message)
            if not author:
                continue

            if author.get("bot"):
                continue

            if not author.get("mod", False):
                continue

            author_id = author.get("id")
            if author_id is None:
                continue

            try:
                author_id = int(author_id)
            except (TypeError, ValueError):
                continue

            msg_type = str(message.get("type") or "").lower()

            if msg_type in {"internal", "note"}:
                staff_discussions[author_id] += 1
            else:
                # Everything else from a staff member is treated as user-facing.
                user_interactions[author_id] += 1

        return user_interactions, staff_discussions

    @commands.Cog.listener()
    async def on_thread_close(self, *args):
        try:
            if not args:
                return

            thread = args[0]

            thread_log = await self.bot.api.get_log(thread.channel.id)
            if not thread_log:
                logger.error("[TopSupporters] Failed to retrieve thread log.")
                return

            user_stats, internal_stats = self._count_from_log(thread_log)

            if not user_stats and not internal_stats:
                logger.warning("[TopSupporters] No stats collected from log data.")
                return

            await asyncio.sleep(2)

            log_channel = self.bot.log_channel
            if not log_channel:
                logger.error("[TopSupporters] Log channel missing.")
                return

            target_message = None

            async for msg in log_channel.history(limit=10):
                if msg.author.id != self.bot.user.id:
                    continue

                if not msg.embeds:
                    continue

                embed = msg.embeds[0]
                embed_text = f"{embed.title or ''}\n{embed.description or ''}".lower()

                matched = False
                for recipient in getattr(thread, "recipients", []):
                    if not recipient:
                        continue

                    if str(recipient.id) in embed_text:
                        matched = True
                        break

                    if str(recipient).lower() in embed_text:
                        matched = True
                        break

                if matched:
                    target_message = msg
                    break

            if not target_message:
                logger.error("[TopSupporters] Failed to find matching close embed.")
                return

            guild = self.bot.modmail_guild or self.bot.guild

            embed = target_message.embeds[0]
            new_embed = discord.Embed.from_dict(embed.to_dict())

            new_embed.add_field(
                name="User Interaction",
                value=self._format_counter(
                    user_stats,
                    guild,
                    "No user-facing staff messages recorded."
                ),
                inline=False,
            )

            new_embed.add_field(
                name="Staff Discussion",
                value=self._format_counter(
                    internal_stats,
                    guild,
                    "No internal staff messages recorded."
                ),
                inline=False,
            )

            await target_message.edit(embed=new_embed)

        except Exception:
            logger.exception("[TopSupporters] Error inside on_thread_close")


async def setup(bot):
    logger.info("[TopSupporters] Loading plugin.")
    await bot.add_cog(TopSupporters(bot))
    logger.info("[TopSupporters] Plugin loaded.")
