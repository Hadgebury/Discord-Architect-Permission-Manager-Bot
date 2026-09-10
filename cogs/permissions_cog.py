import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio
from pathlib import Path
from typing import Optional

from core.dynamic_perms import (
    get_channel_label,
    get_global_perm_names,
    get_channel_perm_names,
    extract_role_permissions,
    extract_channel_overwrites,
    get_zero_trust_channel_perms,
    get_zero_trust_global_perms
)
from core.rate_limiter import PacedExecutor

class PermissionsCog(commands.Cog, name="Permissions"):
    """Manages bulk channel overwrites and server role permissions using dynamic permission discovery."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = getattr(bot, "bot_config", None)
        self.executor = PacedExecutor(
            delay_seconds=self.config.rate_limit_delay_seconds if self.config else 0.25
        )

    def _get_path(self, filename: str) -> Path:
        """Prefers backup_dir if configured, otherwise root path."""
        if self.config and self.config.backup_dir:
            return self.config.backup_dir / filename
        return Path(filename)

    # -------------------------------------------------------------------------
    # CATALOG COMMAND
    # -------------------------------------------------------------------------
    @app_commands.command(
        name="permissions_catalog",
        description="Inspect all permissions dynamically discovered from the current Discord runtime."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def permissions_catalog(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        global_perms = get_global_perm_names()
        channel_perms = get_channel_perm_names()

        embed = discord.Embed(
            title="🔍 Dynamic Permission Catalog",
            description=(
                f"Your bot is running with dynamic introspection enabled.\n"
                f"**discord.py Version:** `{discord.__version__}`\n"
                f"**Global Role Permissions:** `{len(global_perms)}` detected\n"
                f"**Channel Overwrite Permissions:** `{len(channel_perms)}` detected\n\n"
                f"*When Discord adds new permissions and you update discord.py, "
                f"they will automatically show up here without modifying any code.*"
            ),
            color=discord.Color.blue()
        )

        # Show first 15 and sample
        embed.add_field(
            name=f"Sample Global Permissions ({len(global_perms)} total)",
            value="`" + "`, `".join(global_perms[:12]) + f"` ... and {len(global_perms) - 12} more",
            inline=False
        )
        embed.add_field(
            name=f"Sample Channel Overwrites ({len(channel_perms)} total)",
            value="`" + "`, `".join(channel_perms[:12]) + f"` ... and {len(channel_perms) - 12} more",
            inline=False
        )

        await interaction.followup.send(embed=embed)

    # -------------------------------------------------------------------------
    # MODULE 1: CHANNEL OVERWRITES
    # -------------------------------------------------------------------------
    @app_commands.command(name="backup_channels", description="Scans channels and saves current permissions to file.")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup_channels(self, interaction: discord.Interaction):
        await interaction.response.defer()
        backup_data = {}

        # 1. Orphan channels (outside any category)
        orphans = [c for c in interaction.guild.channels if not getattr(c, "category", None) and not isinstance(c, discord.CategoryChannel)]
        orphans.sort(key=lambda c: c.position)
        for c in orphans:
            backup_data[str(c.id)] = extract_channel_overwrites(c)

        # 2. Categories & child channels
        categories = sorted(interaction.guild.categories, key=lambda c: c.position)
        for cat in categories:
            backup_data[str(cat.id)] = extract_channel_overwrites(cat)
            children = sorted(cat.channels, key=lambda c: c.position)
            for c in children:
                backup_data[str(c.id)] = extract_channel_overwrites(c)

        filepath = self._get_path("backup_channels.json")
        # Also maintain root file for backwards compatibility
        root_path = Path("backup_channels.json")
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=4)
        if filepath != root_path:
            with open(root_path, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=4)

        await interaction.followup.send(
            f"✅ **Channel Backup Complete.**\n"
            f"Saved `{len(backup_data)}` channels/categories to `{filepath}`.\n"
            f"Captured all active dynamic permissions from Discord."
        )

    @app_commands.command(name="generate_channel_template", description="Creates a Zero-Trust channel config (All False).")
    @app_commands.checks.has_permissions(administrator=True)
    async def generate_channel_template(self, interaction: discord.Interaction):
        await interaction.response.defer()

        source_file = self._get_path("backup_channels.json")
        if not source_file.exists() and Path("backup_channels.json").exists():
            source_file = Path("backup_channels.json")

        if not source_file.exists():
            await interaction.followup.send(f"❌ Backup file `{source_file}` not found. Run `/backup_channels` first.")
            return

        with open(source_file, "r", encoding="utf-8") as f:
            structure = json.load(f)

        new_config = {}
        all_roles = sorted(interaction.guild.roles, key=lambda r: r.position, reverse=True)
        channel_perms = get_channel_perm_names()

        for channel_id, data in structure.items():
            new_config[channel_id] = {"__channel_name": data.get("__channel_name", "Unknown")}
            for role in all_roles:
                if role.managed and role.name == self.bot.user.name:
                    continue
                role_entry = {"__role_name": role.name}
                for perm in channel_perms:
                    role_entry[perm] = False
                new_config[channel_id][str(role.id)] = role_entry

        target_file = self._get_path("config_channels.json")
        root_file = Path("config_channels.json")

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=4)
        if target_file != root_file:
            with open(root_file, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=4)

        await interaction.followup.send(
            f"✅ **Zero-Trust Channel Template Generated.**\n"
            f"File: `{target_file}`\n"
            f"Includes all `{len(channel_perms)}` dynamic channel permissions."
        )

    @app_commands.command(name="apply_channel_config", description="Applies permissions from config_channels.json.")
    @app_commands.checks.has_permissions(administrator=True)
    async def apply_channel_config(self, interaction: discord.Interaction):
        await interaction.response.defer()

        target_file = self._get_path("config_channels.json")
        if not target_file.exists() and Path("config_channels.json").exists():
            target_file = Path("config_channels.json")

        if not target_file.exists():
            await interaction.followup.send(f"❌ `{target_file}` missing. Generate and edit it first.")
            return

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            await interaction.followup.send(f"❌ JSON parsing error: {e}")
            return

        status_msg = await interaction.followup.send("📂 **Applying Channel Permissions (Paced Execution)...**")

        channels_updated = 0
        total_overwrites_applied = 0

        for cid, roles in data.items():
            if not cid.isdigit():
                continue
            channel = self.bot.get_channel(int(cid))
            if not channel:
                continue

            channel_changed = False
            for rid, perms in roles.items():
                if not rid.isdigit():
                    continue
                role = interaction.guild.get_role(int(rid))
                if not role:
                    continue

                overwrite = channel.overwrites_for(role)
                changed = False
                for p, v in perms.items():
                    if not p.startswith("__") and hasattr(overwrite, p):
                        if getattr(overwrite, p) != v:
                            setattr(overwrite, p, v)
                            changed = True

                if changed:
                    async def apply_ov(ch=channel, ro=role, ow=overwrite):
                        await ch.set_permissions(ro, overwrite=ow)
                    
                    await self.executor.execute_task(apply_ov)
                    total_overwrites_applied += 1
                    channel_changed = True

            if channel_changed:
                channels_updated += 1

        await interaction.followup.send(
            f"✅ **Channel Permissions Finished.**\n"
            f"• Channels updated: `{channels_updated}`\n"
            f"• Overwrites updated: `{total_overwrites_applied}`"
        )

    # -------------------------------------------------------------------------
    # MODULE 2: GLOBAL ROLE PERMISSIONS
    # -------------------------------------------------------------------------
    @app_commands.command(name="backup_global", description="Scans Global Role permissions and saves snapshot.")
    @app_commands.checks.has_permissions(administrator=True)
    async def backup_global(self, interaction: discord.Interaction):
        await interaction.response.defer()
        backup_data = {}
        roles = sorted(interaction.guild.roles, key=lambda r: r.position, reverse=True)

        for role in roles:
            is_bot = " [BOT/MANAGED]" if role.managed else ""
            role_data = {"__role_name": role.name + is_bot}
            role_data.update(extract_role_permissions(role))
            backup_data[str(role.id)] = role_data

        target_file = self._get_path("backup_global.json")
        root_file = Path("backup_global.json")

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(backup_data, f, indent=4)
        if target_file != root_file:
            with open(root_file, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=4)

        await interaction.followup.send(
            f"✅ **Global Role Backup Complete.**\n"
            f"Saved `{len(backup_data)}` roles to `{target_file}`.\n"
            f"Included all `{len(get_global_perm_names())}` dynamic global permissions."
        )

    @app_commands.command(name="generate_global_template", description="Creates Zero-Trust Global config (All False).")
    @app_commands.checks.has_permissions(administrator=True)
    async def generate_global_template(self, interaction: discord.Interaction):
        await interaction.response.defer()

        source_file = self._get_path("backup_global.json")
        if not source_file.exists() and Path("backup_global.json").exists():
            source_file = Path("backup_global.json")

        if not source_file.exists():
            await interaction.followup.send(f"❌ Backup file `{source_file}` not found. Run `/backup_global` first.")
            return

        with open(source_file, "r", encoding="utf-8") as f:
            backup_data = json.load(f)

        new_config = {}
        global_perms = get_global_perm_names()

        for role_id, info in backup_data.items():
            role = interaction.guild.get_role(int(role_id))
            if role and role.managed:
                continue

            role_entry = {"__role_name": info.get("__role_name", "Unknown")}
            for perm in global_perms:
                role_entry[perm] = False
            new_config[role_id] = role_entry

        target_file = self._get_path("config_global.json")
        root_file = Path("config_global.json")

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(new_config, f, indent=4)
        if target_file != root_file:
            with open(root_file, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=4)

        await interaction.followup.send(
            f"✅ **Global Template Generated.**\n"
            f"File: `{target_file}` (Bot/Managed roles excluded).\n"
            f"All `{len(global_perms)}` permissions defaulted to `false`."
        )

    @app_commands.command(name="apply_global_config", description="Applies Global Role permissions from config_global.json.")
    @app_commands.checks.has_permissions(administrator=True)
    async def apply_global_config(self, interaction: discord.Interaction):
        await interaction.response.defer()

        target_file = self._get_path("config_global.json")
        if not target_file.exists() and Path("config_global.json").exists():
            target_file = Path("config_global.json")

        if not target_file.exists():
            await interaction.followup.send(f"❌ `{target_file}` missing. Generate and edit it first.")
            return

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except Exception as e:
            await interaction.followup.send(f"❌ JSON parsing error: {e}")
            return

        success_count = 0
        skipped_count = 0

        for role_id_str, perms in config_data.items():
            if not role_id_str.isdigit():
                continue
            role = interaction.guild.get_role(int(role_id_str))
            if not role:
                continue
            if role.managed:
                skipped_count += 1
                continue

            current_perms = role.permissions
            needs_update = False
            perm_updates = {}

            for perm_name, perm_val in perms.items():
                if perm_name.startswith("__"):
                    continue
                if hasattr(current_perms, perm_name):
                    if getattr(current_perms, perm_name) != perm_val:
                        perm_updates[perm_name] = perm_val
                        needs_update = True

            if needs_update:
                try:
                    new_perms = discord.Permissions(role.permissions.value)
                    new_perms.update(**perm_updates)
                    
                    async def edit_role(r=role, p=new_perms):
                        await r.edit(permissions=p)

                    await self.executor.execute_task(edit_role)
                    success_count += 1
                except discord.Forbidden:
                    print(f"⛔ Cannot edit {role.name}: Role is higher than bot's role.")
                except Exception as e:
                    print(f"❌ Error editing {role.name}: {e}")

        await interaction.followup.send(
            f"✅ **Global Roles Updated:** `{success_count}` roles updated "
            f"(Skipped `{skipped_count}` managed/bot roles)."
        )

async def setup(bot: commands.Bot):
    await bot.add_cog(PermissionsCog(bot))
