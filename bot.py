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