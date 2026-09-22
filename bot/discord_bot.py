"""
Discord bot for the LMS Agent.
Reads messages in the configured channel and replies via bot.commands.handle.

Run:
    python -m bot.discord_bot
"""
import asyncio
import discord
from config.settings import settings
from bot.commands import handle
from core.storage import init_db
from core.utils import logger, ensure_dirs


intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)


@client.event
async def on_ready():
    logger.info(f"Discord bot ready: {client.user}")
    logger.info(f"Watching channel: {settings.discord_channel_id}")
    try:
        channel = client.get_channel(int(settings.discord_channel_id))
        if channel:
            await channel.send("🤖 **LMS Agent online.** Send `/help` for commands.")
    except Exception as e:
        logger.warning(f"Startup message failed: {e}")


@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return
    if message.guild is not None:
        if str(message.channel.id) != str(settings.discord_channel_id):
            return

    content = (message.content or "").strip()
    if not content:
        return

    logger.info(f"[Discord] {message.author}: {content[:80]}")

    async with message.channel.typing():
        try:
            reply = await asyncio.to_thread(handle, content)
        except Exception as e:
            logger.exception("handle failed")
            reply = f"❌ Error: {e}"

    if not reply:
        reply = "(no response)"
    for i in range(0, len(reply), 1900):
        await message.channel.send(reply[i:i + 1900])


def main():
    ensure_dirs()
    init_db()

    if not settings.discord_bot_token:
        logger.error("DISCORD_BOT_TOKEN not set in .env")
        return
    if not settings.discord_channel_id:
        logger.error("DISCORD_CHANNEL_ID not set in .env")
        return

    logger.info("Starting Discord bot...")
    client.run(settings.discord_bot_token, log_handler=None)


if __name__ == "__main__":
    main()
