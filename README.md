# Discord Permission Manager Bot

A powerful, "Infrastructure as Code" style Discord bot that allows server administrators to manage permissions via local JSON files. 

This bot moves away from clicking UI toggles in Discord and allows you to bulk-edit, backup, and deploy permissions for both **Channel Overwrites** and **Global Role Settings** using a "Zero Trust" methodology.

## 🚀 Features

* **Slash Commands:** Uses modern Discord `/` commands for a clean user interface.
* **Zero Trust Architecture:** The template generator defaults all permissions to `false`, forcing you to explicitly whitelist what users can do.
* **Two Distinct Modules:**
    * **Channel Manager:** granularly controls overwrites per channel/category.
    * **Global Manager:** controls Server Settings (Role Permissions).
* **Safety First:**
    * Automatically detects and ignores "Managed Roles" (Integration/Bot roles) in the Global module to prevent breaking other bots.
    * Includes "Human Readable" labels in JSON files so you know exactly which ID belongs to which Channel/Role.
* **Bulk Execution:** Applies hundreds of permission changes in a single command.

## 📋 Prerequisites

1.  **Python 3.8+** installed.
2.  A **Discord Bot Token** with Administrator permissions.
3.  **Privileged Intents** enabled in the Discord Developer Portal:
    * Server Members Intent
    * Message Content Intent

## ⚙️ Installation

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/yourusername/your-repo-name.git](https://github.com/yourusername/your-repo-name.git)
    cd your-repo-name
    ```

2.  **Install dependencies:**
    ```bash
    pip install discord.py
    ```

3.  **Configuration:**
    Open `bot.py` and paste your Bot Token into the configuration section:
    ```python
    TOKEN = 'YOUR_BOT_TOKEN_HERE'
    ```
    > ⚠️ **SECURITY WARNING:** Never commit your actual token to GitHub! If making this repo public, use a `.env` file or environment variables instead.

4.  **Run the Bot:**
    ```bash
    python bot.py
    ```

## 📖 Usage Guide

### Module 1: Channel Permissions
*Manage overwrites for specific channels or categories.*

1.  **Backup Current State:**
    Run `/backup_channels`. This creates `backup_channels.json`, scanning your server structure (sorted by category).
    
2.  **Generate Template:**
    Run `/generate_channel_template`. This creates `config_channels.json`.
    * *Note:* This file includes **every role** for **every channel**.
    * *Note:* All permissions are set to `false` by default.
    
3.  **Edit Configuration:**
    Open `config_channels.json`. Change `false` to `true` for the permissions you wish to grant.
    ```json
    "CHANNEL_ID": {
        "__channel_name": "General > #chat",
        "ROLE_ID": {
             "__role_name": "@Members",
             "send_messages": true,
             "view_channel": true
        }
    }
    ```

4.  **Apply Changes:**
    Run `/apply_channel_config`. The bot will read the file and update Discord in real-time.

---

### Module 2: Global Permissions
*Manage server-wide Role settings (e.g., Administrator, Ban Members).*

1.  **Backup Global Roles:**
    Run `/backup_global`. Saves current role hierarchy to `backup_global.json`.

2.  **Generate Template:**
    Run `/generate_global_template`. This creates `config_global.json`.
    * **Safety Feature:** This command automatically skips "Managed" roles (bots/integrations) to prevent you from accidentally stripping their permissions.

3.  **Edit Configuration:**
    Open `config_global.json` and set your desired permissions.
    > **⚠️ CRITICAL:** Ensure you set `administrator: true` or `manage_roles: true` for your own Admin role, or you risk locking yourself out of the server settings!

4.  **Apply Changes:**
    Run `/apply_global_config`.

## 📂 File Structure

The bot generates JSON files with metadata keys starting with `__`.

* `__channel_name`: "Category Name > #ChannelName"
* `__role_name`: "@RoleName"

These keys are **ignored** by the bot during the Apply phase. They exist solely to help you navigate the file. You do not need to delete them.

## 🛡️ Troubleshooting

* **"Improper token has been passed"**: You likely used the Client Secret instead of the Bot Token, or your token format in `bot.py` is incorrect.
* **Bot doesn't update a specific role**:
    * **Hierarchy:** Check your Discord Server Settings > Roles. The Bot's role **must** be physically higher in the list than the roles it is trying to edit.
    * **Managed Roles:** The Global module intentionally refuses to edit managed roles (like other bots) for safety.
* **JSON Syntax Error**: If the bot fails to read your file, use a [JSON Validator](https://jsonlint.com/) to ensure you didn't miss a comma or bracket while editing.

## 📝 License

[License](https://github.com/Hadgebury/Discord-Permissions-Mass-Updater-Bot/blob/main/LICENSE)
