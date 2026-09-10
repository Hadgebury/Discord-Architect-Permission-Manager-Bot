# Discord Architect & Permission Manager Bot

A modular, **Infrastructure-as-Code (IaC)** and interactive Discord bot designed to build, edit, and manage entire Discord servers. 

Manage permissions, channel hierarchy, categories, and server settings declaratively through local blueprint files, or interactively via modern slash commands. Built with **dynamic Discord introspection**, the bot automatically discovers newly added permissions and settings as Discord and `discord.py` evolve over time.

---

## 🚀 Key Features

* **Dynamic Discord Introspection:**
  * No rigid, hardcoded permission lists. The bot dynamically inspects the Discord runtime, discovering all 56+ role permissions and 35+ channel overwrites.
  * When Discord adds new permissions, simply update `discord.py` (`pip install --upgrade discord.py`) and the bot will recognise and support them immediately without requiring code modifications.
* **Dedicated Configuration File:**
  * Tokens, command prefixes, and operational preferences are stored securely in a dedicated `config.json` (or `.env` file). No secrets or credentials are ever placed inside Python scripts.
* **Hybrid Server Management:**
  * **File-Driven Blueprint Engine (IaC):** Export, dry-run preview, and reconcile complete Discord server structures (categories, channels, layout order, settings, and overwrites).
  * **Interactive Slash Commands:** On-the-fly channel creation, category permission synchronisation, channel cloning, and server settings adjustments.
* **Granular Permission Manager (Zero-Trust):**
  * Mass backup and deployment of channel overwrites and server-wide role permissions.
  * Automatically detects and protects managed integration and bot roles to avoid disrupting third-party bots.
* **Paced API Execution & Safety Guardrails:**
  * Built-in rate-limit throttling and automatic backoff protect against Discord HTTP 429 locks during mass actions.
  * Destructive operations (such as pruning unlisted channels) require explicit interactive button confirmation in Discord.

---

## 📋 Prerequisites & Discord Portal Setup

### 1. System Requirements
* **Python 3.8+** (Python 3.10+ recommended).
* **Git** installed on your system.

### 2. Creating Your Discord Bot Application
1. Navigate to the [Discord Developer Portal](https://discord.com/developers/applications) and log in with your Discord account.
2. Click **New Application** in the top right-hand corner, name your application (e.g. *Server Architect*), and click **Create**.
3. In the left-hand navigation menu, select **Bot**:
   * Click **Reset Token** to generate your Bot Token. Copy this token safely; you will need it shortly.
   * Scroll down to **Privileged Gateway Intents** and enable both:
     * **Server Members Intent** (required to read role hierarchy and members)
     * **Message Content Intent** (required for prefix utility commands like `!sync_commands`)
   * Click **Save Changes**.
4. In the left-hand menu, navigate to **OAuth2** ➔ **URL Generator**:
   * Under **Scopes**, select `bot` and `applications.commands`.
   * Under **Bot Permissions**, select `Administrator` (or explicitly tick `Manage Server`, `Manage Channels`, `Manage Roles`, and `View Audit Log`).
   * Copy the generated URL at the bottom of the page, paste it into your browser, and invite the bot to your target Discord server.

> ⚠️ **Important Hierarchy Rule:** Discord enforces strict role hierarchy. Ensure the bot's own role sits **higher** in Server Settings ➔ Roles than the roles you intend for it to manage, otherwise Discord will reject permission modifications.

---

## ⚙️ Installation & Configuration

### 1. Clone the Repository
```bash
git clone https://github.com/Hadgebury/Discord-Architect-Permission-Manager-Bot.git
cd Discord-Architect-Permission-Manager-Bot
```

### 2. Set Up a Virtual Environment (Optional but Recommended)
```bash
# Windows
python -m venv venv
.\venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Your Bot Credentials
Run the bot once to automatically initialise `config.json`, or copy `config.example.json`:
```bash
# Windows
copy config.example.json config.json

# macOS / Linux
cp config.example.json config.json
```

Open `config.json` in your preferred text editor:
```json
{
  "bot_token": "YOUR_DISCORD_BOT_TOKEN_HERE",
  "command_prefix": "!",
  "dev_guild_id": "YOUR_OPTIONAL_TEST_SERVER_ID_FOR_INSTANT_SYNC",
  "rate_limit_delay_seconds": 0.25,
  "backup_dir": "backups",
  "blueprint_dir": "blueprints"
}
```

#### Configuration Options Explained:
| Option | Type | Description |
| :--- | :--- | :--- |
| `bot_token` | `string` | Your Discord bot token obtained from the Developer Portal. |
| `command_prefix` | `string` | Prefix for fallback text commands (default: `!`). |
| `dev_guild_id` | `string` | Optional Discord Server ID. When set, slash commands synchronise **immediately** to this server upon launch. |
| `rate_limit_delay_seconds` | `float` | Pacing delay between batch API calls to prevent Discord rate limits (default: `0.25`). |
| `backup_dir` | `string` | Local folder where permission backups are stored (default: `backups`). |
| `blueprint_dir` | `string` | Local folder where server layout blueprints are stored (default: `blueprints`). |

> 🔒 **Security Notice:** `config.json` and `.env` are listed in `.gitignore`. Your credentials will never be committed to Git.

### 5. Launch the Bot
```bash
python main.py
# (or python bot.py)
```

Upon launching, the console will output dynamic diagnostics:
```
============================================================
[ONLINE] Logged in as: ServerArchitect#1234 (ID: 1234567890)
[RUNTIME] discord.py Version: 2.6.4
[INTROSPECTION] Dynamic Permissions Discovered:
   * Global Role Permissions: 56
   * Channel Overwrite Permissions: 35
[CONFIG] Dedicated Config File: config.json
[STORAGE] Blueprint Directory: blueprints
============================================================
[READY] Bot is operational. Use /permissions_catalog, /layout_view, or /blueprint_export
```

---

## ⚡ Synchronising Slash Commands

Discord has two types of slash commands:
1. **Guild Commands (Instant):** If you populate `dev_guild_id` in `config.json`, the bot registers commands to that server instantly on startup.
2. **Global Commands:** If no `dev_guild_id` is supplied, commands are registered globally across Discord's CDN, which can take up to an hour to propagate.
3. **Manual Synchronisation:** You can trigger an instant sync at any time by typing:
   ```
   !sync_commands YOUR_SERVER_ID
   ```
   into any channel the bot can see.

---

## 📖 Practical User Workflows

### Workflow 1: Infrastructure-as-Code (Server Blueprints)

A blueprint captures your entire server architecture—including settings, roles, categories, channels, layout positions, topics, slowmodes, and permissions—into a clean, human-readable JSON document.

1. **Export Existing Layout:**
   Run `/blueprint_export filename:my_server.json`.
   The blueprint will be written to `blueprints/my_server.json`.
2. **Review or Edit Locally:**
   Open the blueprint in your text editor. You can alter channel topics, reorder categories, or define new channels.
3. **Dry-Run Preview:**
   Run `/blueprint_preview filename:my_server.json`.
   The bot analyses differences and sends an embed showing exactly which roles, categories, and channels will be created without modifying the live server.
4. **Apply Blueprint:**
   Run `/blueprint_apply filename:my_server.json`.
   The bot paces its requests, builds missing categories and channels, and configures role overwrites.
5. **Testing the Starter Template:**
   A pre-configured template is included in `blueprints/starter_community.json`. You can preview it immediately with:
   `/blueprint_preview filename:starter_community.json`.

---

### Workflow 2: Zero-Trust Permission Overhauls

Zero-Trust permission management defaults every permission to `false`, requiring you to explicitly whitelist only what each role is permitted to do.

1. **Backup Channel Permissions:**
   Run `/backup_channels`. Creates `backups/backup_channels.json` containing current overwrites.
2. **Generate Zero-Trust Template:**
   Run `/generate_channel_template`. Produces `backups/config_channels.json` with all dynamic permissions set to `false`.
3. **Customise Whitelist:**
   Open `config_channels.json`, locate the channel and role, and flip desired permissions to `true`:
   ```json
   "1234567890": {
       "__channel_name": "COMMUNITY > #general",
       "9876543210": {
           "__role_name": "Member",
           "view_channel": true,
           "send_messages": true,
           "read_message_history": true
       }
   }
   ```
4. **Deploy Updates:**
   Run `/apply_channel_config`. The bot iterates through channels and updates overwrites with automatic throttling.
5. **Server-Wide Global Roles:**
   Follow the identical workflow for server-wide roles using `/backup_global`, `/generate_global_template`, and `/apply_global_config`.

---

### Workflow 3: Interactive Server Building

If you prefer on-the-fly server editing in Discord:
* `/layout_view`: Visualises your entire server layout, categories, and channel ordering in an ASCII tree embed.
* `/channel_create`: Interactively creates text, voice, stage, forum, or announcement channels with custom topics and slowmodes.
* `/channel_clone`: Duplicates an existing channel with all of its overwrites intact.
* `/channel_edit`: Modifies channel topics, slowmode, name, or parent category.
* `/category_sync_permissions`: Forces all channels in a category to inherit the category's permission overwrites.
* `/server_settings_view` & `/server_settings_update`: Inspect and modify server verification, notification defaults, AFK settings, and rules channels.

---

## 🔍 Complete Command Reference

| Command | Category | Description | Permissions Required |
| :--- | :--- | :--- | :--- |
| `/permissions_catalog` | Permissions | Displays all role and channel permissions dynamically discovered in the active runtime. | Administrator |
| `/backup_channels` | Permissions | Scans channels and saves existing overwrites to `backup_channels.json`. | Administrator |
| `/generate_channel_template` | Permissions | Creates Zero-Trust `config_channels.json` with all permissions defaulted to `false`. | Administrator |
| `/apply_channel_config` | Permissions | Applies permissions from `config_channels.json` with paced execution. | Administrator |
| `/backup_global` | Permissions | Scans roles and saves current global permissions to `backup_global.json`. | Administrator |
| `/generate_global_template` | Permissions | Generates Zero-Trust `config_global.json` (managed bot roles excluded). | Administrator |
| `/apply_global_config` | Permissions | Applies global role permissions from `config_global.json`. | Administrator |
| `/blueprint_export` | Blueprints | Exports full server layout, settings, roles, and permissions to a blueprint file. | Administrator |
| `/blueprint_preview` | Blueprints | **Dry-Run mode:** Compares blueprint against the live server and previews changes. | Administrator |
| `/blueprint_apply` | Blueprints | Reconciles the live Discord server to match the specified blueprint file. | Administrator |
| `/layout_view` | Layout | Displays an ASCII tree view of all categories, channels, and their ordering. | Manage Channels |
| `/channel_create` | Layout | Creates a customisable text, voice, stage, forum, or announcement channel. | Manage Channels |
| `/channel_edit` | Layout | Edits properties of an existing channel (name, topic, slowmode, category). | Manage Channels |
| `/channel_clone` | Layout | Clones an existing channel, duplicating settings and permission overwrites. | Manage Channels |
| `/category_create` | Layout | Creates a new category at a specified position. | Manage Channels |
| `/category_sync_permissions` | Layout | Synchronises all child channels to match their parent category's permissions. | Manage Channels |
| `/server_settings_view` | Settings | Displays current server verification, AFK, notifications, and system channels. | Manage Server |
| `/server_settings_update` | Settings | Updates server configuration (name, description, AFK timeout, rules channel, etc.). | Manage Server |

---

## 🔄 Keeping Permissions Up To Date

When Discord introduces new permissions (e.g. new voice features, soundboard options, or administration flags), you do not need to update or modify any bot code. 

Simply update `discord.py` in your environment:
```bash
pip install --upgrade discord.py
```

Restart the bot, execute `/permissions_catalog`, and the newly released permissions will immediately be included in all backups, Zero-Trust templates, and server blueprints.

---

## 📂 Project Structure

```
DiscordPermissionsMassUpdaterBot/
│
├── config.json                     # Dedicated configuration file with bot token (ignored by Git)
├── config.example.json             # Version-controlled configuration template
├── main.py                         # Primary bot entry point and execution runner
├── bot.py                          # Backwards-compatible execution alias
├── requirements.txt                # Project dependencies (discord.py, python-dotenv, PyYAML)
├── README.md                       # Comprehensive guide and documentation
├── LICENSE                         # Project licence
├── .gitignore                      # Configured to protect tokens, backups, and user blueprints
│
├── core/                           # Core architecture & framework utilities
│   ├── __init__.py                 # Core package exports
│   ├── bot.py                      # DiscordArchitectBot subclass (lifecycle & extension loader)
│   ├── config.py                   # Dedicated configuration loader with fallback handling
│   ├── dynamic_perms.py            # Dynamic Discord permissions & settings introspection
│   └── rate_limiter.py             # Paced API executor & HTTP 429 automatic backoff
│
├── cogs/                           # Modular slash command extensions
│   ├── __init__.py                 # Cogs package indicator
│   ├── permissions_cog.py          # Dynamic Zero-Trust channel & global role updater
│   ├── layout_cog.py               # Channel & category builder, cloner, and visualizer
│   ├── settings_cog.py             # Server-wide settings inspection & modification
│   └── blueprint_cog.py            # Infrastructure-as-Code export, dry-run, and reconciler
│
├── blueprints/                     # Server blueprints storage
│   ├── .gitkeep                    # Preserves directory in Git
│   └── starter_community.json      # Ready-to-use community server layout template
│
├── backups/                        # Permission backups storage
│   └── .gitkeep                    # Preserves directory in Git
│
└── tests/                          # Automated unit test suite
    ├── __init__.py                 # Tests package indicator
    └── test_engine.py              # Automated tests for dynamic perms, schemas, and cogs
```

---

## 🧪 Running Automated Tests

To execute the test suite:
```bash
python -m unittest discover -s tests
```
The test suite verifies:
* Dynamic discovery of 50+ global permissions and 30+ channel overwrites from `discord.py`.
* Zero-Trust default generation (`all False`).
* Safe loading of `config.json` with fallback handling.
* Server blueprint schema serialisation and diff parsing.
* Successful registration and loading of all four command cogs.

---

## 📄 Licence

This project is licensed under a **Custom Modified MIT Non-Commercial Licence (MIT-NC)** with mandatory author attribution:

* **Free for Personal & Community Use:** You are free to view, use, run, and modify this bot for non-commercial, personal, or educational purposes.
* **Mandatory Attribution:** You must prominently retain the copyright notice and credit the original author (**Hadgebury**) in all copies, substantial portions, or modified/derivative versions.
* **No Commercial Gain:** The software and its derivatives may not be sold, monetized, or used for commercial gain, paid services, or fee-based hosting without the explicit prior written permission of the author.

For the full legal terms, see the [LICENSE](LICENSE) file.
