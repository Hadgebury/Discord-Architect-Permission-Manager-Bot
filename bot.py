import discord
from discord import app_commands
from discord.ext import commands
import json
import os
import asyncio

# ==============================================================================
# CONFIGURATION SECTION
# ==============================================================================

TOKEN = 'YOUR_BOT_TOKEN_HERE'

# FILE NAMES
FILE_BACKUP_CHANNELS = 'backup_channels.json'
FILE_CONFIG_CHANNELS = 'config_channels.json'

FILE_BACKUP_GLOBAL = 'backup_global.json'
FILE_CONFIG_GLOBAL = 'config_global.json'

# ==============================================================================
# PERMISSION REFERENCE LISTS
# ==============================================================================

CHANNEL_PERM_LIST = [
    "view_channel", "manage_channels", "manage_roles", "manage_webhooks",
    "create_instant_invite", "send_messages", "send_messages_in_threads",
    "create_public_threads", "create_private_threads", "manage_threads",
    "manage_messages", "read_message_history", "embed_links", "attach_files",
    "add_reactions", "use_external_emojis", "use_external_stickers",
    "mention_everyone", "use_application_commands", "connect", "speak", "stream",
    "use_voice_activation", "priority_speaker", "mute_members", "deafen_members",
    "move_members", "request_to_speak", "use_soundboard", "use_external_sounds",
    "use_embedded_activities"
]

GLOBAL_PERM_LIST = [
    "administrator", "manage_guild", "manage_roles", "manage_channels",
    "kick_members", "ban_members", "create_instant_invite", "change_nickname",
    "manage_nicknames", "manage_webhooks", "manage_guild_expressions",
    "view_audit_log", "view_guild_insights", "view_creator_monetization_analytics",
    "read_message_history", "send_messages", "send_tts_messages", "manage_messages",
    "embed_links", "attach_files", "read_message_history", "mention_everyone",
    "use_external_emojis", "view_channel", "connect", "speak", "mute_members",
    "deafen_members", "move_members", "use_voice_activation", "priority_speaker",
    "stream", "request_to_speak", "use_application_commands", "use_embedded_activities",
    "use_soundboard", "use_external_sounds", "moderate_members"
]

# ==============================================================================
# BOT SETUP
# ==============================================================================

class PermissionBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        pass

bot = PermissionBot()

@bot.event
async def on_ready():
    print(f'---------------------------------------')
    print(f'Logged in as: {bot.user.name} (ID: {bot.user.id})')
    print(f'✅ Bot is ready.')
    print(f'---------------------------------------')

def get_channel_label(channel):
    if isinstance(channel, discord.CategoryChannel):
        return f"[CATEGORY] {channel.name.upper()}"
    elif channel.category:
        return f"{channel.category.name} > #{channel.name}"
    return f"NO CATEGORY > #{channel.name}"

# ==============================================================================
# MODULE 1: CHANNEL OVERWRITES
# ==============================================================================

@bot.tree.command(name="backup_channels", description="Scans channels and saves FULL EXISTING permissions to file.")
@app_commands.checks.has_permissions(administrator=True)
async def backup_channels(interaction: discord.Interaction):
    """
    Scans the server and creates a complete snapshot of current channel permissions.
    """
    await interaction.response.defer()
    
    backup_data = {}
    
    # Helper to extract data from a specific channel object
    def extract_channel_data(c):
        c_data = {"__channel_name": get_channel_label(c)}
        
        # Iterate over existing overwrites
        for target, overwrite in c.overwrites.items():
            if isinstance(target, discord.Role):
                role_data = {"__role_name": target.name}
                
                # Check every permission in our list
                has_perms = False
                for perm in CHANNEL_PERM_LIST:
                    # getattr returns True, False, or None (Inherit)
                    val = getattr(overwrite, perm, None)
                    if val is not None:
                        role_data[perm] = val
                        has_perms = True
                
                if has_perms:
                    c_data[str(target.id)] = role_data
        return c_data

    # 1. Orphans
    orphans = [c for c in interaction.guild.channels if not c.category and not isinstance(c, discord.CategoryChannel)]
    orphans.sort(key=lambda c: c.position)
    for c in orphans:
        backup_data[str(c.id)] = extract_channel_data(c)

    # 2. Categories & Children
    categories = sorted(interaction.guild.categories, key=lambda c: c.position)
    for cat in categories:
        backup_data[str(cat.id)] = extract_channel_data(cat)
        
        children = sorted(cat.channels, key=lambda c: c.position)
        for c in children:
            backup_data[str(c.id)] = extract_channel_data(c)

    with open(FILE_BACKUP_CHANNELS, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=4)
    
    await interaction.followup.send(f"✅ **Channel Backup Complete.**\nSnapshot saved to `{FILE_BACKUP_CHANNELS}`.\nIt now contains all existing True/False values.")


@bot.tree.command(name="generate_channel_template", description="Creates a Zero-Trust config (All False).")
@app_commands.checks.has_permissions(administrator=True)
async def generate_channel_template(interaction: discord.Interaction):
    """
    Reads the backup structure but ignores values, setting everything to FALSE.
    """
    await interaction.response.defer()
    
    if not os.path.exists(FILE_BACKUP_CHANNELS):
        await interaction.followup.send(f"❌ `{FILE_BACKUP_CHANNELS}` missing.")
        return

    with open(FILE_BACKUP_CHANNELS, 'r', encoding='utf-8') as f:
        structure = json.load(f)

    new_config = {}
    all_roles = sorted(interaction.guild.roles, key=lambda r: r.position, reverse=True)

    for channel_id, data in structure.items():
        new_config[channel_id] = {"__channel_name": data.get("__channel_name", "Unknown")}
        
        for role in all_roles:
            if role.managed and role.name == bot.user.name: continue 

            role_entry = {"__role_name": role.name}
            for perm in CHANNEL_PERM_LIST:
                role_entry[perm] = False
            
            new_config[channel_id][str(role.id)] = role_entry

    with open(FILE_CONFIG_CHANNELS, 'w', encoding='utf-8') as f:
        json.dump(new_config, f, indent=4)

    await interaction.followup.send(f"✅ **Zero-Trust Template Generated.**\nFile: `{FILE_CONFIG_CHANNELS}`.")


@bot.tree.command(name="apply_channel_config", description="Applies the permissions from config_channels.json.")
@app_commands.checks.has_permissions(administrator=True)
async def apply_channel_config(interaction: discord.Interaction):
    await interaction.response.defer()

    if not os.path.exists(FILE_CONFIG_CHANNELS):
        await interaction.followup.send(f"❌ `{FILE_CONFIG_CHANNELS}` missing.")
        return

    try:
        with open(FILE_CONFIG_CHANNELS, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        await interaction.followup.send(f"❌ JSON Error: {e}")
        return

    count = 0
    await interaction.followup.send("📂 **Applying Channel Config...**")

    for cid, roles in data.items():
        if not cid.isdigit(): continue
        channel = bot.get_channel(int(cid))
        if not channel: continue

        for rid, perms in roles.items():
            if not rid.isdigit(): continue
            role = interaction.guild.get_role(int(rid))
            if not role: continue

            overwrite = channel.overwrites_for(role)
            changed = False
            for p, v in perms.items():
                if not p.startswith("__") and hasattr(overwrite, p):
                    if getattr(overwrite, p) != v:
                        setattr(overwrite, p, v)
                        changed = True
            if changed:
                await channel.set_permissions(role, overwrite=overwrite)
                await asyncio.sleep(0.05)
        count += 1
    
    await interaction.followup.send(f"✅ **Finished.** Channels Updated: {count}")

# ==============================================================================
# MODULE 2: GLOBAL ROLE PERMISSIONS
# ==============================================================================

@bot.tree.command(name="backup_global", description="Scans Global Role permissions and saves snapshot.")
@app_commands.checks.has_permissions(administrator=True)
async def backup_global(interaction: discord.Interaction):
    """
    Scans all roles and saves their CURRENT permission settings (True/False).
    """
    await interaction.response.defer()
    
    backup_data = {}
    roles = sorted(interaction.guild.roles, key=lambda r: r.position, reverse=True)
    
    for role in roles:
        is_bot = " [BOT/MANAGED]" if role.managed else ""
        role_data = {"__role_name": role.name + is_bot}
        
        # Capture current values
        for perm in GLOBAL_PERM_LIST:
            if hasattr(role.permissions, perm):
                role_data[perm] = getattr(role.permissions, perm)
        
        backup_data[str(role.id)] = role_data

    with open(FILE_BACKUP_GLOBAL, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, indent=4)
        
    await interaction.followup.send(f"✅ **Global Backup Complete.**\nSnapshot saved to `{FILE_BACKUP_GLOBAL}` with full permission list.")


@bot.tree.command(name="generate_global_template", description="Creates Zero-Trust Global config (All False).")
@app_commands.checks.has_permissions(administrator=True)
async def generate_global_template(interaction: discord.Interaction):
    await interaction.response.defer()

    if not os.path.exists(FILE_BACKUP_GLOBAL):
        await interaction.followup.send(f"❌ `{FILE_BACKUP_GLOBAL}` missing.")
        return

    with open(FILE_BACKUP_GLOBAL, 'r', encoding='utf-8') as f:
        backup_data = json.load(f)

    new_config = {}
    for role_id, info in backup_data.items():
        role = interaction.guild.get_role(int(role_id))
        if role and role.managed: continue

        role_entry = {"__role_name": info.get("__role_name", "Unknown")}
        for perm in GLOBAL_PERM_LIST:
            role_entry[perm] = False
            
        new_config[role_id] = role_entry

    with open(FILE_CONFIG_GLOBAL, 'w', encoding='utf-8') as f:
        json.dump(new_config, f, indent=4)

    await interaction.followup.send(f"✅ **Global Template Generated.**\nFile: `{FILE_CONFIG_GLOBAL}`.\nBot roles excluded.")


@bot.tree.command(name="apply_global_config", description="Applies Global Role config.")
@app_commands.checks.has_permissions(administrator=True)
async def apply_global_config(interaction: discord.Interaction):
    await interaction.response.defer()

    if not os.path.exists(FILE_CONFIG_GLOBAL):
        await interaction.followup.send(f"❌ `{FILE_CONFIG_GLOBAL}` missing.")
        return

    try:
        with open(FILE_CONFIG_GLOBAL, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
    except Exception as e:
        await interaction.followup.send(f"❌ JSON Error: {e}")
        return

    success_count = 0
    await interaction.followup.send("📂 **Applying Global Role Config...**")
    
    for role_id_str, perms in config_data.items():
        if not role_id_str.isdigit(): continue
        role = interaction.guild.get_role(int(role_id_str))
        if not role: continue
        if role.managed: 
            print(f"⛔ Skipping managed role: {role.name}")
            continue

        try:
            current_perms = role.permissions
            needs_update = False
            perm_updates = {}
            
            for perm_name, perm_val in perms.items():
                if perm_name.startswith("__"): continue
                if hasattr(current_perms, perm_name):
                    if getattr(current_perms, perm_name) != perm_val:
                        perm_updates[perm_name] = perm_val
                        needs_update = True
            if needs_update:
                new_perms = role.permissions
                new_perms.update(**perm_updates)
                await role.edit(permissions=new_perms)
                await asyncio.sleep(0.2)
                success_count += 1
        except Exception as e:
            print(f"❌ Error editing {role.name}: {e}")

    await interaction.followup.send(f"✅ **Global Roles Updated:** {success_count}")

# ==============================================================================
# UTILITY
# ==============================================================================

@bot.command(name="fix_duplicates")
@commands.has_permissions(administrator=True)
async def fix_duplicates(ctx):
    """
    Removes Global commands, syncs Guild commands.
    """
    await ctx.send("🧹 **Cleaning up duplicates...**")
    bot.tree.copy_global_to(guild=ctx.guild)
    await bot.tree.sync(guild=ctx.guild)
    bot.tree.clear_commands(guild=None) 
    await bot.tree.sync(guild=None)
    await ctx.send("✅ **Fixed!**")

bot.run(TOKEN)