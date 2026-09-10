import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import discord
from discord import app_commands
from discord.ext import commands

from core.config import BotConfig
from core.dynamic_perms import get_global_perm_names, get_channel_perm_names

class DiscordArchitectBot(commands.Bot):
    """
    Core bot class for Discord Permissions & Server Architecture.
    Handles dynamic cog loading, fast slash command synchronization, and lifecycle logging.
    """

    def __init__(self, config: BotConfig):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True

        super().__init__(
            command_prefix=config.command_prefix,
            intents=intents
        )
        self.bot_config = config

    async def setup_hook(self):
        """Loads all cogs from the cogs directory dynamically."""
        cogs_dir = Path(__file__).resolve().parent.parent / "cogs"
        if cogs_dir.exists():
            for file in cogs_dir.glob("*.py"):
                if file.name.startswith("__"):
                    continue
                cog_name = f"cogs.{file.stem}"
                try:
                    await self.load_extension(cog_name)
                    print(f"[EXT] Loaded extension: {cog_name}")
                except Exception as e:
                    print(f"[ERROR] Failed to load extension {cog_name}: {e}")

        # If dev_guild_id is provided in config, copy and sync commands for instant development
        if self.bot_config.dev_guild_id:
            try:
                guild = discord.Object(id=self.bot_config.dev_guild_id)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                print(f"[FAST-SYNC] Fast-synced slash commands to Dev Guild: {self.bot_config.dev_guild_id}")
            except Exception as e:
                print(f"[WARN] Could not fast-sync to Dev Guild {self.bot_config.dev_guild_id}: {e}")

    async def on_ready(self):
        """Displays startup diagnostics and dynamic inspection stats."""
        global_perms = get_global_perm_names()
        channel_perms = get_channel_perm_names()

        print("=" * 60)
        print(f"[ONLINE] Logged in as: {self.user.name} (ID: {self.user.id})")
        print(f"[RUNTIME] discord.py Version: {discord.__version__}")
        print(f"[INTROSPECTION] Dynamic Permissions Discovered:")
        print(f"   * Global Role Permissions: {len(global_perms)}")
        print(f"   * Channel Overwrite Permissions: {len(channel_perms)}")
        print(f"[CONFIG] Dedicated Config File: config.json")
        print(f"[STORAGE] Blueprint Directory: {self.bot_config.blueprint_dir}")
        print("=" * 60)
        print("[READY] Bot is operational. Use /permissions_catalog, /layout_view, or /blueprint_export")
