import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from core.dynamic_perms import (
    get_channel_label,
    get_global_perm_names,
    get_channel_perm_names,
    extract_role_permissions,
    extract_channel_overwrites,
    get_guild_settings_snapshot
)
from core.rate_limiter import PacedExecutor

class BlueprintConfirmView(discord.ui.View):
    """Interactive confirmation view for destructive actions (e.g. prune)."""
    def __init__(self, author_id: int):
        super().__init__(timeout=60.0)
        self.author_id = author_id
        self.confirmed: Optional[bool] = None

    @discord.ui.button(label="Confirm Prune & Apply", style=discord.ButtonStyle.danger, emoji="⚠️")
    async def confirm_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You are not authorized to confirm this action.", ephemeral=True)
            return
        self.confirmed = True
        self.stop()
        await interaction.response.send_message("⚠️ Confirmation received. Proceeding with prune...", ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.secondary, emoji="❌")
    async def cancel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ You are not authorized to cancel this action.", ephemeral=True)
            return
        self.confirmed = False
        self.stop()
        await interaction.response.send_message("Action cancelled.", ephemeral=True)

class BlueprintCog(commands.Cog, name="Blueprint"):
    """Infrastructure-as-Code engine for Discord: export, dry-run preview, and apply server blueprints."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = getattr(bot, "bot_config", None)
        self.executor = PacedExecutor(
            delay_seconds=self.config.rate_limit_delay_seconds if self.config else 0.25
        )

    def _resolve_blueprint_path(self, filename: str) -> Path:
        """Resolves file path within blueprint_dir or root."""
        clean_name = os.path.basename(filename)
        if not clean_name.endswith(".json"):
            clean_name += ".json"
        
        if self.config and self.config.blueprint_dir:
            return self.config.blueprint_dir / clean_name
        return Path(clean_name)

    def _serialize_channel(self, channel: discord.abc.GuildChannel, include_permissions: bool) -> Dict[str, Any]:
        ch_type = "text"
        if isinstance(channel, discord.VoiceChannel):
            ch_type = "voice"
        elif isinstance(channel, discord.StageChannel):
            ch_type = "stage"
        elif isinstance(channel, discord.ForumChannel):
            ch_type = "forum"
        elif getattr(channel, "is_news", lambda: False)():
            ch_type = "announcement"

        data: Dict[str, Any] = {
            "name": channel.name,
            "type": ch_type,
            "position": channel.position,
            "topic": getattr(channel, "topic", None),
            "slowmode": getattr(channel, "slowmode_delay", 0),
            "nsfw": getattr(channel, "nsfw", False),
        }

        if include_permissions:
            channel_perms = get_channel_perm_names()
            overwrites = {}
            for target, ow in channel.overwrites.items():
                if isinstance(target, discord.Role):
                    r_perms = {}
                    for p in channel_perms:
                        val = getattr(ow, p, None)
                        if val is not None:
                            r_perms[p] = val
                    if r_perms:
                        overwrites[target.name] = {
                            "role_id": str(target.id),
                            "permissions": r_perms
                        }
            data["permissions"] = overwrites

        return data

    # -------------------------------------------------------------------------
    # EXPORT BLUEPRINT
    # -------------------------------------------------------------------------
    @app_commands.command(
        name="blueprint_export",
        description="Exports the full server layout, settings, roles, and permissions to a blueprint file."
    )
    @app_commands.describe(
        filename="Name of blueprint file (default: blueprint.json)",
        include_settings="Include guild settings (name, afk, verification, etc.)",
        include_permissions="Include role permissions and channel overwrites"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def blueprint_export(
        self,
        interaction: discord.Interaction,
        filename: str = "blueprint.json",
        include_settings: bool = True,
        include_permissions: bool = True
    ):
        await interaction.response.defer()
        guild = interaction.guild

        blueprint: Dict[str, Any] = {
            "metadata": {
                "schema_version": "2.0",
                "exported_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "guild_id": str(guild.id),
                "guild_name": guild.name,
                "discord_py_version": discord.__version__
            }
        }

        # 1. Guild Settings
        if include_settings:
            blueprint["settings"] = get_guild_settings_snapshot(guild)

        # 2. Roles
        roles_data = []
        for role in sorted(guild.roles, key=lambda r: r.position, reverse=True):
            if role.is_default():  # @everyone
                roles_data.append({
                    "name": "@everyone",
                    "id": str(role.id),
                    "permissions": extract_role_permissions(role) if include_permissions else {}
                })
            elif not role.managed:
                roles_data.append({
                    "name": role.name,
                    "id": str(role.id),
                    "color": str(role.color),
                    "hoist": role.hoist,
                    "mentionable": role.mentionable,
                    "permissions": extract_role_permissions(role) if include_permissions else {}
                })
        blueprint["roles"] = roles_data

        # 3. Categories & Channels
        categories_data = []
        for cat in sorted(guild.categories, key=lambda c: c.position):
            cat_data: Dict[str, Any] = {
                "name": cat.name,
                "position": cat.position,
                "channels": []
            }
            if include_permissions:
                cat_overwrites = {}
                for target, ow in cat.overwrites.items():
                    if isinstance(target, discord.Role):
                        r_perms = {}
                        for p in get_channel_perm_names():
                            val = getattr(ow, p, None)
                            if val is not None:
                                r_perms[p] = val
                        if r_perms:
                            cat_overwrites[target.name] = {
                                "role_id": str(target.id),
                                "permissions": r_perms
                            }
                cat_data["permissions"] = cat_overwrites

            for ch in sorted(cat.channels, key=lambda c: c.position):
                cat_data["channels"].append(self._serialize_channel(ch, include_permissions))

            categories_data.append(cat_data)
        blueprint["categories"] = categories_data

        # 4. Orphans (channels without category)
        orphans = [c for c in guild.channels if not getattr(c, "category", None) and not isinstance(c, discord.CategoryChannel)]
        orphans.sort(key=lambda c: c.position)
        blueprint["orphan_channels"] = [
            self._serialize_channel(c, include_permissions) for c in orphans
        ]

        target_path = self._resolve_blueprint_path(filename)
        root_path = Path(filename if filename.endswith(".json") else f"{filename}.json")

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(blueprint, f, indent=4)
        if target_path != root_path:
            with open(root_path, "w", encoding="utf-8") as f:
                json.dump(blueprint, f, indent=4)

        total_channels = len(guild.channels)
        await interaction.followup.send(
            f"✅ **Blueprint Exported Successfully!**\n"
            f"• File: `{target_path}`\n"
            f"• Categories: `{len(categories_data)}`\n"
            f"• Channels: `{total_channels}`\n"
            f"• Roles: `{len(roles_data)}`"
        )

    # -------------------------------------------------------------------------
    # PREVIEW BLUEPRINT (DRY-RUN)
    # -------------------------------------------------------------------------
    @app_commands.command(
        name="blueprint_preview",
        description="Dry-run: compares a blueprint against the live server and previews changes."
    )
    @app_commands.describe(filename="Blueprint file to preview (default: blueprint.json)")
    @app_commands.checks.has_permissions(administrator=True)
    async def blueprint_preview(self, interaction: discord.Interaction, filename: str = "blueprint.json"):
        await interaction.response.defer()
        target_path = self._resolve_blueprint_path(filename)
        if not target_path.exists() and Path(filename).exists():
            target_path = Path(filename)

        if not target_path.exists():
            await interaction.followup.send(f"❌ Blueprint file `{target_path}` not found.")
            return

        with open(target_path, "r", encoding="utf-8") as f:
            bp = json.load(f)

        guild = interaction.guild

        # Analyze differences
        existing_roles = {r.name.lower(): r for r in guild.roles}
        existing_categories = {c.name.lower(): c for c in guild.categories}
        existing_channels = {c.name.lower(): c for c in guild.channels if not isinstance(c, discord.CategoryChannel)}

        roles_to_create = []
        for r in bp.get("roles", []):
            if r["name"] != "@everyone" and r["name"].lower() not in existing_roles:
                roles_to_create.append(r["name"])

        categories_to_create = []
        channels_to_create = []
        for cat in bp.get("categories", []):
            if cat["name"].lower() not in existing_categories:
                categories_to_create.append(cat["name"])
            for ch in cat.get("channels", []):
                if ch["name"].lower() not in existing_channels:
                    channels_to_create.append(f"#{ch['name']} (in {cat['name']})")

        for ch in bp.get("orphan_channels", []):
            if ch["name"].lower() not in existing_channels:
                channels_to_create.append(f"#{ch['name']} (standalone)")

        embed = discord.Embed(
            title=f"🔎 Blueprint Dry-Run Preview: `{filename}`",
            description="Comparing blueprint against current server state:",
            color=discord.Color.blue()
        )

        embed.add_field(
            name=f"➕ Roles to Create ({len(roles_to_create)})",
            value="`" + "`, `".join(roles_to_create[:10]) + "`" if roles_to_create else "*(All roles exist)*",
            inline=False
        )

        embed.add_field(
            name=f"📂 Categories to Create ({len(categories_to_create)})",
            value="`" + "`, `".join(categories_to_create[:10]) + "`" if categories_to_create else "*(All categories exist)*",
            inline=False
        )

        embed.add_field(
            name=f"💬 Channels to Create ({len(channels_to_create)})",
            value="\n".join(channels_to_create[:10]) if channels_to_create else "*(All channels exist)*",
            inline=False
        )

        await interaction.followup.send(embed=embed)

    # -------------------------------------------------------------------------
    # APPLY BLUEPRINT
    # -------------------------------------------------------------------------
    @app_commands.command(
        name="blueprint_apply",
        description="Reconciles the Discord server to match the blueprint file."
    )
    @app_commands.describe(
        filename="Blueprint file to apply",
        prune="DANGER: Delete channels/categories not present in the blueprint (Requires Confirmation)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def blueprint_apply(
        self,
        interaction: discord.Interaction,
        filename: str = "blueprint.json",
        prune: bool = False
    ):
        await interaction.response.defer()
        target_path = self._resolve_blueprint_path(filename)
        if not target_path.exists() and Path(filename).exists():
            target_path = Path(filename)

        if not target_path.exists():
            await interaction.followup.send(f"❌ Blueprint file `{target_path}` not found.")
            return

        with open(target_path, "r", encoding="utf-8") as f:
            bp = json.load(f)

        guild = interaction.guild

        if prune:
            view = BlueprintConfirmView(author_id=interaction.user.id)
            prompt = await interaction.followup.send(
                "⚠️ **PRUNE MODE IS ENABLED:** Any channel or category on this server that is NOT listed in the blueprint will be **permanently deleted**!\n"
                "Please click below to confirm or cancel.",
                view=view
            )
            await view.wait()
            if view.confirmed is not True:
                await interaction.followup.send("❌ Blueprint application cancelled.")
                return

        status_msg = await interaction.followup.send("🚀 **Applying Blueprint (Paced Execution)...**")

        # 1. Sync Roles
        roles_by_name = {r.name.lower(): r for r in guild.roles}
        for r_spec in bp.get("roles", []):
            r_name = r_spec.get("name")
            if not r_name or r_name == "@everyone":
                continue

            role = roles_by_name.get(r_name.lower())
            if not role:
                color_val = discord.Color.default()
                if "color" in r_spec and r_spec["color"]:
                    try:
                        color_val = discord.Color.from_str(r_spec["color"])
                    except Exception:
                        pass
                
                async def create_r(n=r_name, c=color_val, h=r_spec.get("hoist", False), m=r_spec.get("mentionable", False)):
                    return await guild.create_role(name=n, color=c, hoist=h, mentionable=m, reason="Blueprint apply")

                role = await self.executor.execute_task(create_r)
                if role:
                    roles_by_name[role.name.lower()] = role

        # 2. Sync Categories
        categories_by_name = {c.name.lower(): c for c in guild.categories}
        for cat_spec in bp.get("categories", []):
            cat_name = cat_spec.get("name")
            cat = categories_by_name.get(cat_name.lower())
            if not cat:
                async def create_cat(n=cat_name, pos=cat_spec.get("position", 0)):
                    return await guild.create_category(name=n, position=pos, reason="Blueprint apply")
                cat = await self.executor.execute_task(create_cat)
                if cat:
                    categories_by_name[cat.name.lower()] = cat

            # Create channels inside category
            for ch_spec in cat_spec.get("channels", []):
                ch_name = ch_spec.get("name")
                ch_type = ch_spec.get("type", "text")
                existing = discord.utils.get(cat.channels, name=ch_name)
                if not existing:
                    async def create_ch(n=ch_name, t=ch_type, parent=cat, s=ch_spec):
                        if t == "voice":
                            return await guild.create_voice_channel(name=n, category=parent)
                        elif t == "stage":
                            return await guild.create_stage_channel(name=n, category=parent, topic=s.get("topic"))
                        elif t == "forum":
                            return await guild.create_forum(name=n, category=parent, topic=s.get("topic"))
                        else:
                            return await guild.create_text_channel(
                                name=n, category=parent, topic=s.get("topic"),
                                slowmode_delay=s.get("slowmode", 0), nsfw=s.get("nsfw", False)
                            )
                    existing = await self.executor.execute_task(create_ch)

                # Apply Overwrites if available
                if existing and "permissions" in ch_spec:
                    for role_target_name, p_data in ch_spec["permissions"].items():
                        target_role = discord.utils.get(guild.roles, name=role_target_name)
                        if target_role:
                            ow = existing.overwrites_for(target_role)
                            for perm_k, perm_v in p_data.get("permissions", {}).items():
                                if hasattr(ow, perm_k):
                                    setattr(ow, perm_k, perm_v)
                            async def set_ov(c=existing, r=target_role, o=ow):
                                await c.set_permissions(r, overwrite=o)
                            await self.executor.execute_task(set_ov)

        # 3. Sync Standalone Channels
        for ch_spec in bp.get("orphan_channels", []):
            ch_name = ch_spec.get("name")
            ch_type = ch_spec.get("type", "text")
            existing = discord.utils.get(guild.channels, name=ch_name)
            if not existing or existing.category is not None:
                async def create_standalone(n=ch_name, t=ch_type, s=ch_spec):
                    if t == "voice":
                        return await guild.create_voice_channel(name=n)
                    elif t == "stage":
                        return await guild.create_stage_channel(name=n, topic=s.get("topic"))
                    elif t == "forum":
                        return await guild.create_forum(name=n, topic=s.get("topic"))
                    else:
                        return await guild.create_text_channel(
                            name=n, topic=s.get("topic"),
                            slowmode_delay=s.get("slowmode", 0), nsfw=s.get("nsfw", False)
                        )
                await self.executor.execute_task(create_standalone)

        await interaction.followup.send(
            f"✅ **Blueprint Reconciled Successfully!**\n"
            f"Server `{guild.name}` layout and channels updated from `{filename}`."
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(BlueprintCog(bot))
