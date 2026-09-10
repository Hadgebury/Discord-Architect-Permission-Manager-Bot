import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Literal
from core.dynamic_perms import get_guild_settings_snapshot

VerificationLevelLiteral = Literal["none", "low", "medium", "high", "highest"]
NotificationLevelLiteral = Literal["all_messages", "only_mentions"]
ContentFilterLiteral = Literal["disabled", "no_role", "all_members"]
AfkTimeoutLiteral = Literal[60, 300, 900, 1800, 3600]

class SettingsCog(commands.Cog, name="ServerSettings"):
    """Manages Discord server (guild) configuration and administrative settings."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="server_settings_view", description="Displays current server configuration and settings.")
    @app_commands.checks.has_permissions(manage_guild=True)
    async def server_settings_view(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild
        snapshot = get_guild_settings_snapshot(guild)

        embed = discord.Embed(
            title=f"⚙️ Server Settings: {guild.name}",
            description=snapshot.get("description") or "*(No description set)*",
            color=discord.Color.gold()
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(name="🛡️ Verification Level", value=f"`{snapshot['verification_level']}`", inline=True)
        embed.add_field(name="🔔 Default Notifications", value=f"`{snapshot['default_notifications']}`", inline=True)
        embed.add_field(name="🔞 Explicit Content Filter", value=f"`{snapshot['explicit_content_filter']}`", inline=True)

        afk_chan = f"#{snapshot['afk_channel']}" if snapshot['afk_channel'] else "None"
        embed.add_field(name="💤 AFK Channel & Timeout", value=f"{afk_chan} ({snapshot['afk_timeout']}s)", inline=True)

        sys_chan = f"#{snapshot['system_channel']}" if snapshot['system_channel'] else "None"
        embed.add_field(name="📢 System Messages Channel", value=sys_chan, inline=True)

        rules_chan = f"#{snapshot['rules_channel']}" if snapshot['rules_channel'] else "None"
        embed.add_field(name="📜 Rules Channel", value=rules_chan, inline=True)

        safety_chan = f"#{snapshot['safety_alerts_channel']}" if snapshot.get('safety_alerts_channel') else "None"
        embed.add_field(name="🚨 Safety Alerts Channel", value=safety_chan, inline=True)

        embed.add_field(
            name="📊 Boost Progress Bar",
            value="Enabled" if snapshot['premium_progress_bar_enabled'] else "Disabled",
            inline=True
        )

        await interaction.followup.send(embed=embed)

    @app_commands.command(name="server_settings_update", description="Modifies server-wide settings.")
    @app_commands.describe(
        name="Update server name",
        description="Update server description",
        verification_level="Set server verification level",
        default_notifications="Set default notification settings",
        explicit_content_filter="Set explicit media content filtering",
        afk_channel="Voice channel for inactive members",
        afk_timeout="Inactivity timeout before moving to AFK (seconds)",
        system_channel="Channel for Discord system messages",
        rules_channel="Channel for server rules and community guidelines"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def server_settings_update(
        self,
        interaction: discord.Interaction,
        name: Optional[str] = None,
        description: Optional[str] = None,
        verification_level: Optional[VerificationLevelLiteral] = None,
        default_notifications: Optional[NotificationLevelLiteral] = None,
        explicit_content_filter: Optional[ContentFilterLiteral] = None,
        afk_channel: Optional[discord.VoiceChannel] = None,
        afk_timeout: Optional[AfkTimeoutLiteral] = None,
        system_channel: Optional[discord.TextChannel] = None,
        rules_channel: Optional[discord.TextChannel] = None
    ):
        await interaction.response.defer()
        guild = interaction.guild
        kwargs = {}

        if name is not None:
            kwargs["name"] = name
        if description is not None:
            kwargs["description"] = description
        if verification_level is not None:
            kwargs["verification_level"] = discord.VerificationLevel[verification_level]
        if default_notifications is not None:
            kwargs["default_notifications"] = discord.NotificationLevel[default_notifications]
        if explicit_content_filter is not None:
            kwargs["explicit_content_filter"] = discord.ContentFilter[explicit_content_filter]
        if afk_channel is not None:
            kwargs["afk_channel"] = afk_channel
        if afk_timeout is not None:
            kwargs["afk_timeout"] = afk_timeout
        if system_channel is not None:
            kwargs["system_channel"] = system_channel
        if rules_channel is not None:
            kwargs["rules_channel"] = rules_channel

        if not kwargs:
            await interaction.followup.send("⚠️ No settings to update were provided.")
            return

        try:
            await guild.edit(**kwargs, reason=f"Updated by {interaction.user}")
            updated_fields = ", ".join([f"`{k}`" for k in kwargs.keys()])
            await interaction.followup.send(f"✅ Successfully updated server settings: {updated_fields}")
        except discord.Forbidden:
            await interaction.followup.send("❌ Failed: Bot lacks permission to modify one or more server settings.")
        except Exception as e:
            await interaction.followup.send(f"❌ Error updating server settings: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(SettingsCog(bot))
