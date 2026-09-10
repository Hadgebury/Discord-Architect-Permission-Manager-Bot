import sys
from typing import Optional

# Ensure safe console output on Windows cp1252
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import discord
from discord.ext import commands

from core import load_config, DiscordArchitectBot

def run():
    config = load_config()

    if not config.is_token_configured:
        print("\n" + "!" * 60)
        print("[WARNING] BOT TOKEN NOT CONFIGURED")
        print("!" * 60)
        print("A dedicated config file has been created at:\n  -> config.json\n")
        print("Please open 'config.json' and paste your bot token into the 'bot_token' field:")
        print('  "bot_token": "your_token_here"\n')
        print("Alternatively, you can set the environment variable:")
        print("  set DISCORD_BOT_TOKEN=your_token_here (Windows)")
        print("  export DISCORD_BOT_TOKEN=your_token_here (Linux/Mac)\n")
        print("!" * 60 + "\n")
        sys.exit(1)

    bot = DiscordArchitectBot(config)

    # Prefix command for manual slash command sync
    @bot.command(name="sync_commands")
    @commands.has_permissions(administrator=True)
    async def sync_commands(ctx, guild_id: Optional[str] = None):
        """Syncs slash commands globally or to a specific guild for instant testing."""
        await ctx.send("🔄 **Syncing slash commands...**")
        try:
            if guild_id:
                target_guild = discord.Object(id=int(guild_id))
                bot.tree.copy_global_to(guild=target_guild)
                synced = await bot.tree.sync(guild=target_guild)
                await ctx.send(f"✅ Synced `{len(synced)}` commands to Guild `{guild_id}` (Instant).")
            else:
                synced = await bot.tree.sync()
                await ctx.send(f"✅ Synced `{len(synced)}` commands Globally (may take up to 1 hour to propagate).")
        except Exception as e:
            await ctx.send(f"❌ Sync failed: {e}")

    try:
        bot.run(config.bot_token)
    except discord.LoginFailure:
        print("\n[ERROR] Discord Login Failure: The provided bot token in config.json is invalid.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Bot shut down cleanly.")

if __name__ == "__main__":
    run()
