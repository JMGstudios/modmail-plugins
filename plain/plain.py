import discord
from discord.ext import commands


class Plain(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="plain")
    async def plain(self, ctx, message_id: int, mode: str = None):
        """
        Usage:
        .plain <message_id>
        .plain <message_id> cb
        """

        try:
            message = await ctx.channel.fetch_message(message_id)
        except discord.NotFound:
            return await ctx.send("Message not found")
        except discord.Forbidden:
            return await ctx.send("No permission to read the message.")
        except discord.HTTPException:
            return await ctx.send("Error. Try again")

        content = None

        # 1. Plain text
        if message.content:
            content = message.content

        # 2. Embed
        elif message.embeds:
            embed = message.embeds[0]

            if embed.description:
                content = embed.description
            elif embed.fields:
                content = "\n".join(f"{f.name}: {f.value}" for f in embed.fields)

        if not content:
            return await ctx.send("No content found")

        # Codeblock mode
        if mode == "cb":
            content = f"```{content}```"

        # send INTERNAL
        await ctx.send(content)


async def setup(bot):
    await bot.add_cog(Plain(bot))
