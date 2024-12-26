import logging
import random
import praw

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Chat,      # <-- Added
    Message    # <-- Added
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# -----------------------------------------------------------------------------
# 1) Logging (for debugging)
# -----------------------------------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# -----------------------------------------------------------------------------
# 2) Credentials (Replace placeholders with your actual tokens/keys)
# -----------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = "7378773393:AAFiwJD2nXX5OO5TJCuJc9QNdNct9jm1AKA"

# Reddit PRAW credentials
REDDIT_CLIENT_ID = "4wIjtWb2Ij5bb5U7KHDTHQ"
REDDIT_SECRET = "kepmR74UKUY0HthwPoMf1hcou1OQ5g"
REDDIT_USER_AGENT = "memesbot"

# -----------------------------------------------------------------------------
# 3) Initialize Reddit (PRAW)
# -----------------------------------------------------------------------------
reddit = praw.Reddit(
    client_id="4wIjtWb2Ij5bb5U7KHDTHQ",  # <-- must be in quotes, so Python recognizes it as a string
    client_secret="kepmR74UKUY0HthwPoMf1hcou1OQ5g",
    user_agent="memesbot by /u/YourRedditUsername"
)

# -----------------------------------------------------------------------------
# 4) Helper: Fetch a Meme from r/memes
# -----------------------------------------------------------------------------
def fetch_meme(sort: str = "hot", time_filter: str = "day", limit: int = 50):
    """
    Fetch one (title, url) from r/memes using a chosen 'sort':
      - 'hot', 'new', 'random', or 'top'
    'time_filter' only applies if sort == 'top' (e.g. 'day', 'week', etc.)
    Returns (title, url) or (None, None) if none found.
    """
    subreddit = reddit.subreddit("memes")

    if sort == "hot":
        posts = list(subreddit.hot(limit=limit))
    elif sort == "new":
        posts = list(subreddit.new(limit=limit))
    elif sort == "wholesomememes":
        attempts = 30
        for i in range(attempts):
            submission = subreddit.random()
            logging.info(f"Attempt {i + 1}, got submission = {submission}")
            if (
                    submission
                    and not submission.stickied
                    and submission.url.endswith((".jpg", ".jpeg", ".png", ".gif"))
            ):
                logging.info(f"Found random valid submission: {submission.title}")
                return (submission.title, submission.url)

        logging.warning("No valid random post found after 10 attempts; falling back to hot.")
        posts = list(subreddit.hot(limit=limit))
    elif sort == "top":
        posts = list(subreddit.top(time_filter=time_filter, limit=limit))
    else:
        posts = list(subreddit.hot(limit=limit))

    random.shuffle(posts)
    for submission in posts:
        if submission.url.endswith((".jpg", ".jpeg", ".png", ".gif")) and not submission.stickied:
            return (submission.title, submission.url)
    return (None, None)

# -----------------------------------------------------------------------------
# 5) Show Main Menu (Helper)
# -----------------------------------------------------------------------------
async def show_main_menu(obj):
    """
    Displays the "main menu" with 4 inline buttons:
    - Hot Meme
    - New Meme
    - Random Meme
    - Top Meme (Week)
    
    If `obj` is a Chat, we can .send_message(...) directly.
    If `obj` is a Message, we should delete the old message, then send a new one via .chat.
    """
    keyboard = [
        [
            InlineKeyboardButton("🔥 Hot Meme", callback_data="hot|day"),
            InlineKeyboardButton("🆕 New Meme", callback_data="new|day"),
        ],
        [
            InlineKeyboardButton("🎲 Random Meme", callback_data="random|day"),
            InlineKeyboardButton("🏆 Top Meme (Week)", callback_data="top|week"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if isinstance(obj, Chat):
        # It's a Chat object
        await obj.send_message(
            text="Choose a meme style:",
            reply_markup=reply_markup
        )
    elif isinstance(obj, Message):
        # It's a Message object
        await obj.delete()
        await obj.chat.send_message(
            text="Choose a meme style:",
            reply_markup=reply_markup
        )
    else:
        # Fallback, shouldn't normally happen
        logging.warning("show_main_menu received an unknown object type.")

# -----------------------------------------------------------------------------
# 6) /start Command
# -----------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Greet the user with a minimal message, plus the main menu.
    """
    await update.message.reply_text(
        "Welcome to Meme Bot!\n"
        "Choose a meme style below or use /newmeme to fetch memes with text commands."
    )
    # Show the main menu in a new message
    await show_main_menu(update.message.chat)

# -----------------------------------------------------------------------------
# 7) /newmeme Command
# -----------------------------------------------------------------------------
async def new_meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /newmeme [sort] [time_filter]
    e.g. /newmeme hot, /newmeme random, /newmeme top week, etc.
    If no arguments -> defaults to 'hot day'
    """
    args = context.args
    sort = "hot"
    time_filter = "day"

    if len(args) > 0:
        sort = args[0].lower()
    if sort == "top" and len(args) > 1:
        time_filter = args[1].lower()

    title, meme_url = fetch_meme(sort=sort, time_filter=time_filter)
    if meme_url:
        # We'll store callback_data in the format "sort|time_filter"
        cb_data = f"{sort}|{time_filter}"

        # We add two buttons: "Next Meme" & "Return to Menu"
        keyboard = [
            [InlineKeyboardButton("Next Meme", callback_data=cb_data)],
            [InlineKeyboardButton("Return to Menu", callback_data="return_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.effective_chat.send_photo(
            photo=meme_url,
            caption=title or "Meme",
            reply_markup=reply_markup
        )
    else:
        await update.effective_chat.send_message("Sorry, no memes found right now.")

# -----------------------------------------------------------------------------
# 8) Callback for Inline Buttons
# -----------------------------------------------------------------------------
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Triggered when user taps an inline button:
      - Could be from the main menu (like 'hot|day')
      - Could be "Next Meme" (also 'hot|day' etc.)
      - Could be "Return to Menu" => 'return_menu'
    """
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "return_menu":
        # Return the user to the main menu
        await show_main_menu(query.message)
        return

    # Otherwise, data is "sort|time_filter", like "hot|day"
    sort, time_filter = data.split("|")
    # fetch a new meme
    title, meme_url = fetch_meme(sort=sort, time_filter=time_filter)
    if meme_url:
        # same callback_data for "Next Meme"
        cb_data = f"{sort}|{time_filter}"

        keyboard = [
            [InlineKeyboardButton("Next Meme", callback_data=cb_data)],
            [InlineKeyboardButton("Return to Menu", callback_data="return_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # If the original message had a photo, we can just edit that message
        if query.message.photo:
            new_media = InputMediaPhoto(media=meme_url, caption=title or "Meme")
            await query.edit_message_media(
                media=new_media,
                reply_markup=reply_markup
            )
        else:
            # If it was a text-based message, we can delete and send a new photo
            await query.message.delete()
            await query.message.chat.send_photo(
                photo=meme_url,
                caption=title or "Meme",
                reply_markup=reply_markup
            )
    else:
        # If no meme found, remove buttons
        await query.edit_message_text("No more memes found right now.")

# -----------------------------------------------------------------------------
# 9) Main: Build and Run the Bot
# -----------------------------------------------------------------------------
def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("newmeme", new_meme_command))

    # Callback Handler (for inline buttons)
    app.add_handler(CallbackQueryHandler(button_callback))

    # Run the bot
    app.run_polling()

# -----------------------------------------------------------------------------
# 10) If run directly
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    main()