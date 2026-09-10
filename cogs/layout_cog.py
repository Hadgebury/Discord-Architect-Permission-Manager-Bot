import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional, Literal
from core.rate_limiter import PacedExecutor

ChannelTypeLiteral = Literal["text", "voice", "stage", "forum", "announcement"]

class LayoutCog(commands.Cog, name="Layout"):
    """Interactive management for Discord server layout, channels, and categories."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = getattr(bot, "bot_config", None)
        self.executor = PacedExecutor(
            delay_seconds=self.config.rate_limit_delay_seconds if self.config else 0.25
        )

    # -------------------------------------------------------------------------
    # LAYOUT VIEW
    # -------------------------------------------------------------------------
    @app_commands.command(name="layout_view", description="Displays visual tree of categories and channels.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def layout_view(self, interaction: discord.Interaction):
        await interaction.response.defer()
        guild = interaction.guild

        orphans = [c for c in guild.channels if not getattr(c, "category", None) and not isinstance(c, discord.CategoryChannel)]
        orphans.sort(key=lambda c: c.position)
        categories = sorted(guild.categories, key=lambda c: c.position)

        lines = [f"**Server Layout:** `{guild.name}` ({len(guild.channels)} channels total)\n"]

        if orphans:
            lines.append("📁 **(No Category)**")
            for c in orphans:
                icon = "🔊" if isinstance(c, discord.VoiceChannel) else "💬"
                lines.append(f"  └─ {icon} `#{c.name}` (pos: {c.position})")

        for cat in categories:
            lines.append(f"📂 **{cat.name.upper()}** (pos: {cat.position})")
            children = sorted(cat.channels, key=lambda c: c.position)
            if not children:
                lines.append("  └─ *(empty category)*")
            else:
                for idx, c in enumerate(children):
                    is_last = (idx == len(children) - 1)
                    branch = "└─" if is_last else "├─"
                    icon = "🔊" if isinstance(c, discord.VoiceChannel) else "💬"
                    lines.append(f"  {branch} {icon} `#{c.name}`")

        # Split into embeds if text is long
        full_text = "\n".join(lines)
        if len(full_text) > 4000:
            full_text = full_text[:3900] + "\n\n*(Truncated due to Discord character limits)*"

        embed = discord.Embed(
            title="🗺️ Discord Server Layout",
            description=full_text,
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)

    # -------------------------------------------------------------------------
    # CHANNEL CREATION
    # -------------------------------------------------------------------------
    @app_commands.command(name="channel_create", description="Creates a new channel with customizable settings.")
    @app_commands.describe(
        name="Name of the new channel",
        channel_type="Type of channel (text, voice, stage, forum, announcement)",
        category="Category to place the channel in",
        topic="Channel topic / description",
        slowmode="Slowmode in seconds (0 to 21600)",
        nsfw="Age-restricted / NSFW flag"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def channel_create(
        self,
        interaction: discord.Interaction,
        name: str,
        channel_type: ChannelTypeLiteral = "text",
        category: Optional[discord.CategoryChannel] = None,
        topic: Optional[str] = None,
        slowmode: Optional[int] = None,
        nsfw: bool = False
    ):
        await interaction.response.defer()
        guild = interaction.guild

        try:
            created_channel = None
            if channel_type == "text":
                created_channel = await guild.create_text_channel(
                    name=name,
                    category=category,
                    topic=topic,
                    slowmode_delay=slowmode or 0,
                    nsfw=nsfw
                )
            elif channel_type == "voice":
                created_channel = await guild.create_voice_channel(
                    name=name,
                    category=category
                )
            elif channel_type == "stage":
                created_channel = await guild.create_stage_channel(
                    name=name,
                    category=category,
                    topic=topic
                )
            elif channel_type == "forum":
                created_channel = await guild.create_forum(
                    name=name,
                    category=category,
                    topic=topic,
                    nsfw=nsfw
                )
            elif channel_type == "announcement":
                created_channel = await guild.create_text_channel(
                    name=name,
                    category=category,
                    topic=topic,
                    news=True,
                    nsfw=nsfw
                )

            cat_label = f" in **{category.name}**" if category else " without category"
            await interaction.followup.send(f"✅ Created {channel_type} channel {created_channel.mention}{cat_label}!")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to create channel: {e}")

    # -------------------------------------------------------------------------
    # CHANNEL CLONE
    # -------------------------------------------------------------------------
    @app_commands.command(name="channel_clone", description="Clones an existing channel along with its overwrites.")
    @app_commands.describe(
        source_channel="Channel to clone",
        new_name="Name for the new cloned channel"
    )
    @app_commands.checks.has_permissions(manage_channels=True)
    async def channel_clone(
        self,
        interaction: discord.Interaction,
        source_channel: discord.abc.GuildChannel,
        new_name: str
    ):
        await interaction.response.defer()
        try:
            cloned = await source_channel.clone(name=new_name, reason=f"Cloned by {interaction.user}")
            await interaction.followup.send(f"✅ Successfully cloned {source_channel.name} into {cloned.mention}!")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to clone channel: {e}")

    # -------------------------------------------------------------------------
    # CHANNEL EDIT
    # -------------------------------------------------------------------------
    @app_commands.command(name="channel_edit", description="Edits properties of an existing channel.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def channel_edit(
        self,
        interaction: discord.Interaction,
        channel: discord.abc.GuildChannel,
        name: Optional[str] = None,
        category: Optional[discord.CategoryChannel] = None,
        topic: Optional[str] = None,
        slowmode: Optional[int] = None,
        nsfw: Optional[bool] = None
    ):
        await interaction.response.defer()
        updates = {}
        if name is not None: updates["name"] = name
        if category is not None: updates["category"] = category
        if topic is not None and hasattr(channel, "topic"): updates["topic"] = topic
        if slowmode is not None and hasattr(channel, "slowmode_delay"): updates["slowmode_delay"] = slowmode
        if nsfw is not None and hasattr(channel, "nsfw"): updates["nsfw"] = nsfw

        if not updates:
            await interaction.followup.send("⚠️ No update parameters provided.")
            return

        try:
            await channel.edit(**updates, reason=f"Edited by {interaction.user}")
            await interaction.followup.send(f"✅ Updated channel {channel.name} ({', '.join(updates.keys())}).")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to edit channel: {e}")

    # -------------------------------------------------------------------------
    # CATEGORY CREATE
    # -------------------------------------------------------------------------
    @app_commands.command(name="category_create", description="Creates a new category.")
    @app_commands.checks.has_permissions(manage_channels=True)
    async def category_create(
        self,
        interaction: discord.Interaction,
        name: str,
        position: Optional[int] = None
    ):
        await interaction.response.defer()
        try:
            cat = await interaction.guild.create_category(
                name=name,
                position=position if position is not None else 0
            )
            await interaction.followup.send(f"✅ Created category **{cat.name}** at position `{cat.position}`.")
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to create category: {e}")

    # -------------------------------------------------------------------------
    # CATEGORY SYNC PERMISSIONS
    # -------------------------------------------------------------------------
    @app_commands.command(
        name="category_sync_permissions",
        description="Syncs all channels within a category to match the category's permissions."
    )
    @app_commands.checks.has_permissions(manage_channels=True, manage_roles=True)
    async def category_sync_permissions(
        self,
        interaction: discord.Interaction,
        category: discord.CategoryChannel
    ):
        await interaction.response.defer()
        channels = category.channels
        if not channels:
            await interaction.followup.send(f"⚠️ Category **{category.name}** contains no channels to sync.")
            return

        synced_count = 0
        for ch in channels:
            async def sync_ch(c=ch):
                await c.edit(sync_permissions=True, reason=f"Synced by {interaction.user}")
            await self.executor.execute_task(sync_ch)
            synced_count += 1

        await interaction.followup.send(
            f"✅ Synced permissions for `{synced_count}` channels in **{category.name}**."
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(LayoutCog(bot))
