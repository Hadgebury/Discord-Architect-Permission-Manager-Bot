"""
Core module for Discord Architect Bot.
Provides configuration, dynamic introspection, rate limiting, and the core Bot class.
"""

from core.config import load_config, BotConfig
from core.bot import DiscordArchitectBot
from core.dynamic_perms import (
    get_channel_label,
    get_global_perm_names,
    get_channel_perm_names,
    extract_role_permissions,
    extract_channel_overwrites,
    get_zero_trust_channel_perms,
    get_zero_trust_global_perms,
    get_guild_settings_snapshot,
)
from core.rate_limiter import PacedExecutor

__all__ = [
    "load_config",
    "BotConfig",
    "DiscordArchitectBot",
    "get_channel_label",
    "get_global_perm_names",
    "get_channel_perm_names",
    "extract_role_permissions",
    "extract_channel_overwrites",
    "get_zero_trust_channel_perms",
    "get_zero_trust_global_perms",
    "get_guild_settings_snapshot",
    "PacedExecutor",
]
