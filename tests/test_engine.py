import unittest
import json
import asyncio
from pathlib import Path
import discord
from discord.ext import commands

from core.config import load_config, BotConfig
from core.dynamic_perms import (
    get_global_perm_names,
    get_channel_perm_names,
    get_zero_trust_global_perms,
    get_zero_trust_channel_perms,
    get_channel_label
)
from core.rate_limiter import PacedExecutor

class TestDiscordArchitect(unittest.TestCase):

    def test_dynamic_permissions(self):
        global_perms = get_global_perm_names()
        channel_perms = get_channel_perm_names()

        # discord.py 2.4+ has 50+ permissions
        self.assertGreaterEqual(len(global_perms), 50)
        self.assertIn("manage_channels", global_perms)
        self.assertIn("administrator", global_perms)
        self.assertIn("create_polls", global_perms)

        # Channel permissions
        self.assertGreaterEqual(len(channel_perms), 30)
        self.assertIn("send_messages", channel_perms)
        self.assertIn("view_channel", channel_perms)

    def test_zero_trust_defaults(self):
        zt_global = get_zero_trust_global_perms()
        zt_channel = get_zero_trust_channel_perms()

        self.assertTrue(all(val is False for val in zt_global.values()))
        self.assertTrue(all(val is False for val in zt_channel.values()))
        self.assertEqual(len(zt_global), len(get_global_perm_names()))
        self.assertEqual(len(zt_channel), len(get_channel_perm_names()))

    def test_config_loader(self):
        config = load_config()
        self.assertIsInstance(config, BotConfig)
        self.assertTrue(config.backup_dir.exists())
        self.assertTrue(config.blueprint_dir.exists())

    def test_blueprint_schema_structure(self):
        sample_bp = {
            "metadata": {
                "schema_version": "2.0",
                "guild_name": "Test Server"
            },
            "settings": {
                "name": "Test Server",
                "verification_level": "medium"
            },
            "roles": [
                {"name": "Admin", "permissions": {"administrator": True}}
            ],
            "categories": [
                {
                    "name": "GENERAL",
                    "position": 0,
                    "channels": [
                        {"name": "welcome", "type": "text", "slowmode": 0}
                    ]
                }
            ],
            "orphan_channels": []
        }
        raw_json = json.dumps(sample_bp)
        parsed = json.loads(raw_json)
        self.assertEqual(parsed["metadata"]["schema_version"], "2.0")
        self.assertEqual(len(parsed["categories"]), 1)
        self.assertEqual(parsed["categories"][0]["channels"][0]["name"], "welcome")

    def test_cogs_load_successfully(self):
        async def load_all():
            config = load_config()
            intents = discord.Intents.default()
            bot = commands.Bot(command_prefix="!", intents=intents)
            bot.bot_config = config
            
            cogs = ["cogs.permissions_cog", "cogs.layout_cog", "cogs.settings_cog", "cogs.blueprint_cog"]
            for cog in cogs:
                await bot.load_extension(cog)
            
            return len(bot.cogs), [cmd.name for cmd in bot.tree.get_commands()]

        loop = asyncio.new_event_loop()
        cog_count, command_names = loop.run_until_complete(load_all())
        loop.close()

        self.assertEqual(cog_count, 4)
        self.assertIn("permissions_catalog", command_names)
        self.assertIn("backup_channels", command_names)
        self.assertIn("channel_create", command_names)
        self.assertIn("category_create", command_names)
        self.assertIn("server_settings_view", command_names)
        self.assertIn("blueprint_export", command_names)
        self.assertIn("blueprint_apply", command_names)

if __name__ == "__main__":
    unittest.main()
