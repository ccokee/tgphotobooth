# TGPhotoBooth Telegram Bot

A Telegram bot designed to store images, GIFs, and videos sent by group administrators into a specified directory on a Raspberry Pi (or any Linux-based system). The bot automatically updates a playlist for a slideshow display using VLC in fullscreen mode.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [1. Set Up the System](#1-set-up-the-system)
  - [2. Install Required Software](#2-install-required-software)
  - [3. Create the Project Directory](#3-create-the-project-directory)
  - [4. Set Up a Python Virtual Environment](#4-set-up-a-python-virtual-environment)
  - [5. Install Python Dependencies](#5-install-python-dependencies)
  - [6. Create the Bot Script](#6-create-the-bot-script)
  - [7. Create the `.env` File](#7-create-the-env-file)
  - [8. Create the Images Directory](#8-create-the-images-directory)
  - [9. Adjust Permissions](#9-adjust-permissions)
  - [10. Create a Systemd Service for the Bot](#10-create-a-systemd-service-for-the-bot)
  - [11. Start and Enable the Bot Service](#11-start-and-enable-the-bot-service)
  - [12. Configure VLC Autostart in LXDE](#12-configure-vlc-autostart-in-lxde)
  - [13. Reboot the System](#13-reboot-the-system)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)
- [Project Structure](#project-structure)
- [Code Explanation](#code-explanation)
- [Dependencies](#dependencies)
- [Security Considerations](#security-considerations)
- [Contributing](#contributing)
- [License](#license)

---

## Features

- **Media Reception:** Administrators can send images, GIFs, and videos to the bot for storage.
- **Automatic Playlist Generation:** The bot generates and updates a `.m3u` playlist with the stored media.
- **Slideshow Display:** VLC plays the media in fullscreen slideshow mode on the system.
- **Supported Formats:** Images (`.jpg`, `.jpeg`, `.png`), GIFs (as `.mp4`), and videos (`.mp4`).

## Prerequisites

- A Raspberry Pi or any Linux-based system with the LXDE desktop environment.
- Python 3.7 or higher.
- A Telegram bot token obtained from [BotFather](https://core.telegram.org/bots#6-botfather).
- Internet connection for the system.

## Installation

### 1. Set Up the System

Ensure your system is up to date:

```bash
sudo apt update
sudo apt upgrade -y
```

### 2. Install Required Software

Install Python 3 and VLC:

```bash
sudo apt install -y python3 python3-venv vlc
```

### 3. Create the Project Directory

Create a directory for the bot and navigate into it:

```bash
mkdir -p /home/dietpi/tgphotobooth
cd /home/dietpi/tgphotobooth
```

Replace `/home/dietpi` with your user's home directory if different.

### 4. Set Up a Python Virtual Environment

Create and activate a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 5. Install Python Dependencies

Create a `requirements.txt` file:

```bash
nano requirements.txt
```

Paste the following content:

```
python-telegram-bot==20.3
python-dotenv==1.0.0
```

Save and exit (`Ctrl + X`, then `Y`, and `Enter`).

Install the dependencies:

```bash
pip install -r requirements.txt
```

### 6. Create the Bot Script

Create a new file named `tgphotobooth.py`:

```bash
nano tgphotobooth.py
```

Paste the following code into the file:

```python
import os
import logging
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Load environment variables from the .env file
load_dotenv()

# Global configuration
BOT_TOKEN = os.getenv("BOT_TOKEN")
IMAGE_PATH = os.getenv("IMAGE_PATH", "/home/dietpi/tgphotobooth/pictures")
PLAYLIST_PATH = os.getenv("PLAYLIST_PATH", "/home/dietpi/tgphotobooth/playlist.m3u")

# Logging configuration
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Ensure that the image directory exists
if not os.path.exists(IMAGE_PATH):
    os.makedirs(IMAGE_PATH)

def generate_playlist():
    """Generates the playlist in .m3u format with images, GIFs, and videos."""
    try:
        with open(PLAYLIST_PATH, "w") as playlist:
            playlist.write("#EXTM3U\n")
            # Get the list of files and sort them by modification date
            files = [
                f for f in os.listdir(IMAGE_PATH)
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.mp4'))
            ]
            files.sort(key=lambda x: os.path.getmtime(os.path.join(IMAGE_PATH, x)))
            for file in files:
                # Write the absolute path to the playlist
                playlist.write(f"{os.path.abspath(os.path.join(IMAGE_PATH, file))}\n")
        logger.info("Playlist updated: %s", PLAYLIST_PATH)
    except Exception as e:
        logger.error("Error generating playlist: %s", e)

# Generate the playlist at startup
generate_playlist()

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Bot activated. Only administrators can store images or GIFs."
    )

# Function to handle images, GIFs, and videos sent by administrators
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user

    # Check if the user is an administrator
    admins = await context.bot.get_chat_administrators(chat.id)
    if any(admin.user.id == user.id for admin in admins):
        if update.message.photo:
            keyboard = [["Store image", "Do not store"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            await update.message.reply_text(
                "Do you want to store this image?",
                reply_markup=reply_markup,
            )
            context.user_data["media"] = update.message.photo[-1].file_id
            context.user_data["media_type"] = "photo"
        elif update.message.animation:
            keyboard = [["Store GIF", "Do not store"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            await update.message.reply_text(
                "Do you want to store this GIF?",
                reply_markup=reply_markup,
            )
            context.user_data["media"] = update.message.animation.file_id
            context.user_data["media_type"] = "gif"
        elif update.message.video:
            keyboard = [["Store video", "Do not store"]]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
            await update.message.reply_text(
                "Do you want to store this video?",
                reply_markup=reply_markup,
            )
            context.user_data["media"] = update.message.video.file_id
            context.user_data["media_type"] = "video"
    else:
        await update.message.reply_text(
            "Only administrators can store images or GIFs."
        )

# Function to handle the administrator's decision on the media
async def handle_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_response = update.message.text.lower()
    media_file_id = context.user_data.get("media")
    media_type = context.user_data.get("media_type")

    if user_response in ["store image", "store gif", "store video"] and media_file_id:
        try:
            media_file = await context.bot.get_file(media_file_id)
            if media_type == "photo":
                file_extension = ".jpg"
            elif media_type == "gif":
                file_extension = ".mp4"  # Telegram sends GIFs as MP4 videos
            elif media_type == "video":
                file_extension = ".mp4"
            else:
                await update.message.reply_text(
                    "Unsupported file type.", reply_markup=ReplyKeyboardRemove()
                )
                return

            file_name = f"{media_file_id}{file_extension}"
            file_path = os.path.join(IMAGE_PATH, file_name)
            await media_file.download_to_drive(file_path)
            await update.message.reply_text(f"File stored at {file_path}")
            generate_playlist()
        except Exception as e:
            logger.error("Error storing file: %s", e)
            await update.message.reply_text(
                "Error storing the file.", reply_markup=ReplyKeyboardRemove()
            )
    elif user_response == "do not store":
        await update.message.reply_text(
            "Content discarded.", reply_markup=ReplyKeyboardRemove()
        )
    else:
        await update.message.reply_text(
            "Could not process your response.", reply_markup=ReplyKeyboardRemove()
        )

# Bot setup
def main():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(
        MessageHandler(
            filters.PHOTO | filters.ANIMATION | filters.VIDEO, handle_media
        )
    )
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_decision)
    )

    logger.info("Bot started.")
    application.run_polling()

if __name__ == "__main__":
    main()
```

Save and exit.

### 7. Create the `.env` File

Create a file named `.env` in `/home/dietpi/tgphotobooth/`:

```bash
nano .env
```

Add the following content:

```
BOT_TOKEN=YOUR_BOT_TOKEN
IMAGE_PATH=/home/dietpi/tgphotobooth/pictures
PLAYLIST_PATH=/home/dietpi/tgphotobooth/playlist.m3u
```

Replace `YOUR_BOT_TOKEN` with your actual Telegram bot token obtained from BotFather.

Save and exit.

### 8. Create the Images Directory

Ensure the directory for storing media exists:

```bash
mkdir -p /home/dietpi/tgphotobooth/pictures
```

### 9. Adjust Permissions

Set the appropriate permissions for the directories:

```bash
sudo chown -R dietpi:dietpi /home/dietpi/tgphotobooth
chmod -R u+rw /home/dietpi/tgphotobooth
```

Replace `dietpi` with your username if different.

### 10. Create a Systemd Service for the Bot

Create a service file:

```bash
sudo nano /etc/systemd/system/tgphotobooth.service
```

Paste the following content:

```ini
[Unit]
Description=Telegram PhotoBooth Bot
After=network.target

[Service]
ExecStart=/home/dietpi/tgphotobooth/venv/bin/python /home/dietpi/tgphotobooth/tgphotobooth.py
WorkingDirectory=/home/dietpi/tgphotobooth/
Restart=always
User=dietpi
Group=dietpi

[Install]
WantedBy=multi-user.target
```

Save and exit.

### 11. Start and Enable the Bot Service

Reload systemd to recognize the new service:

```bash
sudo systemctl daemon-reload
```

Enable the service to start on boot:

```bash
sudo systemctl enable tgphotobooth.service
```

Start the service:

```bash
sudo systemctl start tgphotobooth.service
```

Check the service status:

```bash
sudo systemctl status tgphotobooth.service
```

### 12. Configure VLC Autostart in LXDE

Edit the LXDE autostart file:

```bash
nano ~/.config/lxsession/LXDE/autostart
```

If the file or directory doesn't exist, create them.

Add the following line:

```plaintext
@vlc --fullscreen --loop --no-video-title-show --playlist-autostart --playlist-tree --repeat --stop-time=10 --image-duration=10 --no-random /home/dietpi/tgphotobooth/playlist.m3u
```

Save and exit.

### 13. Reboot the System

Reboot to apply changes:

```bash
sudo reboot
```

Upon reboot, the bot will start, and VLC will display the slideshow in fullscreen mode.

## Usage

- **Adding the Bot to a Telegram Group:**
  - Add your bot to a Telegram group.
  - Ensure the bot has admin privileges if necessary.

- **Storing Media:**
  - As a group administrator, send an image, GIF, or video to the group.
  - The bot will ask if you want to store the media.
  - Reply with "Store image", "Store GIF", or "Store video" to save the media.
  - The media is saved to `/home/dietpi/tgphotobooth/pictures`.

- **Playlist Update:**
  - The bot updates `playlist.m3u` whenever new media is stored.
  - VLC reads from `playlist.m3u` and updates the slideshow accordingly.

## Troubleshooting

- **Bot Not Responding:**
  - Check the bot service status:

    ```bash
    sudo systemctl status tgphotobooth.service
    ```

  - Check logs for errors in `/var/log/syslog` or the console where the bot runs.

- **VLC Not Displaying Slideshow:**
  - Ensure the autostart configuration is correct.
  - Verify that `playlist.m3u` exists and is populated.

- **Permission Issues:**
  - Ensure the `dietpi` user (or the user running the bot) has read/write permissions to the directories.

- **Media Not Displayed:**
  - Confirm that media files are in supported formats.
  - VLC may not support certain codecs or file types without additional plugins.

## Project Structure

```
/home/dietpi/tgphotobooth/
├── venv/                   # Python virtual environment
├── tgphotobooth.py         # Main bot script
├── .env                    # Environment variables configuration
├── requirements.txt        # Python dependencies
├── pictures/               # Directory where media files are stored
└── playlist.m3u            # Playlist file for VLC
```

## Code Explanation

- **Imports and Configuration:**
  - Imports necessary modules and sets up logging.
  - Loads environment variables from the `.env` file.

- **generate_playlist Function:**
  - Creates or updates the `.m3u` playlist file.
  - Includes all supported media files from the `pictures` directory.

- **Telegram Bot Handlers:**
  - **start Handler:**
    - Responds to the `/start` command.
  - **handle_media Handler:**
    - Checks if the sender is an admin.
    - Handles incoming photos, animations (GIFs), and videos.
    - Asks the admin whether to store the media.
  - **handle_decision Handler:**
    - Processes the admin's decision.
    - Stores the media if confirmed.
    - Calls `generate_playlist()` to update the playlist.

- **Main Function:**
  - Sets up the bot application.
  - Adds handlers.
  - Starts the bot polling loop.

## Dependencies

- **Python Packages:**
  - `python-telegram-bot==20.3`: For interacting with the Telegram Bot API.
  - `python-dotenv==1.0.0`: For loading environment variables from a `.env` file.

- **System Packages:**
  - `vlc`: For media playback.
  - `python3-venv`: For creating a virtual environment.

## Security Considerations

- **Bot Token:**
  - Keep your `BOT_TOKEN` secret.
  - Do not share it or commit it to a public repository.

- **Permissions:**
  - Ensure that only trusted administrators can interact with the bot to store media.

- **User Data:**
  - The bot stores media files locally; ensure the system is secure.

## Contributing

Contributions are welcome. Please submit a pull request or open an issue to discuss improvements or report bugs.

## License

This project is licensed under the MIT License.

---

**Note:** Replace `/home/dietpi` with the appropriate user directory if your username is different.

**Disclaimer:** Use this bot responsibly and ensure compliance with Telegram's terms of service and local regulations.