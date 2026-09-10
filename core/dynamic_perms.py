import discord
from typing import Dict, List, Optional, Any

def get_channel_label(channel: discord.abc.GuildChannel) -> str:
    """Returns a readable label for a channel or category."""
    if isinstance(channel, discord.CategoryChannel):
        return f"[CATEGORY] {channel.name.upper()}"
    elif getattr(channel, "category", None):
        return f"{channel.category.name} > #{channel.name}"
    return f"NO CATEGORY > #{channel.name}"

def get_global_perm_names() -> List[str]:
    """
    Dynamically discovers all global role permissions available in the installed discord.py version.
    As Discord and discord.py add new permissions, this list automatically updates.
    """
    if hasattr(discord.Permissions, "VALID_FLAGS"):
        return sorted(list(discord.Permissions.VALID_FLAGS.keys()))
    # Fallback to instance iteration if VALID_FLAGS is ever relocated
    return sorted([p for p, _ in discord.Permissions.all()])

def get_channel_perm_names() -> List[str]:
    """
    Dynamically discovers all permissions applicable to channel overwrites.
    Uses all_channel() where available, combined with PermissionOverwrite.VALID_NAMES.
    """
    perms = set()
    if hasattr(discord.Permissions, "all_channel"):
        for p, v in discord.Permissions.all_channel():
            if v:
                perms.add(p)
    
    if hasattr(discord.PermissionOverwrite, "VALID_NAMES"):
        # We focus on the channel-relevant subset or all valid overwrite names
        perms.update(discord.PermissionOverwrite.VALID_NAMES)

    return sorted(list(perms))

def extract_role_permissions(role: discord.Role) -> Dict[str, bool]:
    """Extracts all dynamic global permissions for a role."""
    data = {}
    for perm_name in get_global_perm_names():
        if hasattr(role.permissions, perm_name):
            data[perm_name] = getattr(role.permissions, perm_name)
    return data

def extract_channel_overwrites(channel: discord.abc.GuildChannel) -> Dict[str, Dict[str, Any]]:
    """
    Extracts all existing role overwrites for a specific channel/category.
    Returns a dict keyed by role ID with explicit True/False permissions.
    """
    channel_data: Dict[str, Dict[str, Any]] = {"__channel_name": get_channel_label(channel)}
    channel_perms = get_channel_perm_names()

    for target, overwrite in channel.overwrites.items():
        if isinstance(target, discord.Role):
            role_data: Dict[str, Any] = {"__role_name": target.name}
            has_perms = False
            for perm in channel_perms:
                val = getattr(overwrite, perm, None)
                if val is not None:
                    role_data[perm] = val
                    has_perms = True
            if has_perms:
                channel_data[str(target.id)] = role_data

    return channel_data

def get_zero_trust_channel_perms() -> Dict[str, bool]:
    """Generates a zero-trust (all False) dictionary for channel permissions."""
    return {perm: False for perm in get_channel_perm_names()}

def get_zero_trust_global_perms() -> Dict[str, bool]:
    """Generates a zero-trust (all False) dictionary for global role permissions."""
    return {perm: False for perm in get_global_perm_names()}

def get_guild_settings_snapshot(guild: discord.Guild) -> Dict[str, Any]:
    """Captures key server settings in a structured, declarative format."""
    return {
        "name": guild.name,
        "description": guild.description,
        "afk_timeout": guild.afk_timeout,
        "afk_channel": guild.afk_channel.name if guild.afk_channel else None,
        "system_channel": guild.system_channel.name if guild.system_channel else None,
        "rules_channel": guild.rules_channel.name if guild.rules_channel else None,
        "public_updates_channel": guild.public_updates_channel.name if guild.public_updates_channel else None,
        "safety_alerts_channel": guild.safety_alerts_channel.name if getattr(guild, "safety_alerts_channel", None) else None,
        "verification_level": guild.verification_level.name,
        "default_notifications": guild.default_notifications.name,
        "explicit_content_filter": guild.explicit_content_filter.name,
        "premium_progress_bar_enabled": guild.premium_progress_bar_enabled,
    }
