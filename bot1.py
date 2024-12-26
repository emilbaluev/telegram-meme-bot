import logging
import random
import praw

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Chat,
    Message
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# -----------------------------------------------------------------------------
# Global Variables
# -----------------------------------------------------------------------------
meme_cache = []  # Local cache for storing memes

# -----------------------------------------------------------------------------
# Reddit API Setup
# -----------------------------------------------------------------------------
REDDIT_CLIENT_ID = "4wIjtWb2Ij5bb5U7KHDTHQ"
REDDIT_SECRET = "kepmR74UKUY0HthwPoMf1hcou1OQ5g"
REDDIT_USER_AGENT = "memesbot"

reddit = praw.Reddit(
    client_id="4wIjtWb2Ij5bb5U7KHDTHQ",  # <-- must be in quotes, so Python recognizes it as a string
    client_secret="kepmR74UKUY0HthwPoMf1hcou1OQ5g",
    user_agent="memesbot by /u/YourRedditUsername"
)
# -----------------------------------------------------------------------------
# Meme Cache Management
# -----------------------------------------------------------------------------
def update_meme_cache(limit=100):
    global meme_cache
    subreddit = reddit.subreddit("memes")
    posts = list(subreddit.hot(limit=limit))
    meme_cache = [
        (post.title, post.url) for post in posts
        if post.url.endswith((".jpg", ".jpeg", ".png", ".gif")) and not post.stickied
    ]

def fetch_meme_from_cache():
    global meme_cache
    if not meme_cache:
        update_meme_cache()
    return random.choice(meme_cache)

# -----------------------------------------------------------------------------
# Fetch Meme Logic
# -----------------------------------------------------------------------------
def fetch_meme(sort: str = "hot", time_filter: str = "day", limit: int = 50):
    if sort == "random":
        return fetch_meme_from_cache()

    subreddit = reddit.subreddit("memes")
    if sort == "hot":
        posts = list(subreddit.hot(limit=limit))
    elif sort == "new":
        posts = list(subreddit.new(limit=limit))
    elif sort == "top":
        posts = list(subreddit.top(time_filter=time_filter, limit=limit))
    else:
        posts = list(subreddit.hot(limit=limit))

    for submission in posts:
        if submission.url.endswith((".jpg", ".jpeg", ".png", ".gif")) and not submission.stickied:
            return (submission.title, submission.url)

    return (None, None)

# -----------------------------------------------------------------------------
# Bot Commands and Callbacks
# -----------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Meme Bot! Choose a meme style below."
    )
    await show_main_menu(update.message.chat)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обрабатывает нажатие кнопок: "Next Meme" или "Return to Menu".
    """
    query = update.callback_query
    await query.answer()

    data = query.data
    logging.info(f"Callback data received: {data}")

    if data == "return_menu":
        # Возвращаем пользователя в главное меню
        await show_main_menu(query.message)
        return

    # Если формат callback_data - "sort|time_filter"
    try:
        sort, time_filter = data.split("|")
    except ValueError:
        logging.error("Invalid callback_data format. Expected 'sort|time_filter'.")
        await query.edit_message_text("Ошибка: Неправильный формат данных кнопки.")
        return

    # Получаем мем
    title, url = fetch_meme(sort=sort, time_filter=time_filter)
    if url:
        cb_data = f"{sort}|{time_filter}"
        keyboard = [
            [InlineKeyboardButton("Next Meme", callback_data=cb_data)],
            [InlineKeyboardButton("Return to Menu", callback_data="return_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Если это фото, редактируем его
        if query.message.photo:
            new_media = InputMediaPhoto(media=url, caption=title or "Meme")
            try:
                await query.edit_message_media(media=new_media, reply_markup=reply_markup)
            except Exception as e:
                logging.error(f"Failed to edit message media: {e}")
                await query.message.chat.send_photo(photo=url, caption=title, reply_markup=reply_markup)
        else:
            # Если это текст, удаляем старое сообщение и отправляем новое фото
            await query.message.delete()
            await query.message.chat.send_photo(photo=url, caption=title, reply_markup=reply_markup)
    else:
        await query.edit_message_text("No memes available right now!")

async def show_main_menu(chat_or_message):
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

    if isinstance(chat_or_message, Chat):
        await chat_or_message.send_message("Choose a meme style:", reply_markup=reply_markup)
    elif isinstance(chat_or_message, Message):
        await chat_or_message.delete()
        await chat_or_message.chat.send_message("Choose a meme style:", reply_markup=reply_markup)

# -----------------------------------------------------------------------------
# Main Function
# -----------------------------------------------------------------------------
def main():
    update_meme_cache()  # Populate the cache at startup
    app = ApplicationBuilder().token("7378773393:AAFiwJD2nXX5OO5TJCuJc9QNdNct9jm1AKA").build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling()

if __name__ == "__main__":
    main()

import logging
import random
import praw

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InputMediaPhoto,
    Chat,
    Message
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

# -----------------------------------------------------------------------------
# Global Variables
# -----------------------------------------------------------------------------
meme_cache = []  # Cache to store memes

# -----------------------------------------------------------------------------
# Reddit API Setup
# -----------------------------------------------------------------------------
REDDIT_CLIENT_ID = "4wIjtWb2Ij5bb5U7KHDTHQ"
REDDIT_SECRET = "kepmR74UKUY0HthwPoMf1hcou1OQ5g"
REDDIT_USER_AGENT = "memesbot"

reddit = praw.Reddit(
    client_id="4wIjtWb2Ij5bb5U7KHDTHQ",  # <-- must be in quotes, so Python recognizes it as a string
    client_secret="kepmR74UKUY0HthwPoMf1hcou1OQ5g",
    user_agent="memesbot by /u/YourRedditUsername"
)

# -----------------------------------------------------------------------------
# Meme Cache Management
# -----------------------------------------------------------------------------
def update_meme_cache(limit=100):
    """
    Fetch a fresh batch of memes from Reddit and store them in the cache.
    Randomly choose sorting to ensure variety.
    """
    global meme_cache
    subreddit = reddit.subreddit("memes")

    # Randomly choose a sorting type
    sort = random.choice(["hot", "new", "top"])
    if sort == "hot":
        posts = list(subreddit.hot(limit=limit))
    elif sort == "new":
        posts = list(subreddit.new(limit=limit))
    elif sort == "top":
        posts = list(subreddit.top(time_filter="day", limit=limit))

    meme_cache = [
        (post.title, post.url) for post in posts
        if post.url.endswith((".jpg", ".jpeg", ".png", ".gif")) and not post.stickied
    ]
    random.shuffle(meme_cache)  # Shuffle the cache for randomness

def fetch_meme_from_cache():
    """
    Fetch a random meme from the local cache. Refill the cache if needed.
    """
    global meme_cache
    if len(meme_cache) <= 5:  # Refresh when the cache is low
        update_meme_cache()
    return meme_cache.pop()  # Remove and return a meme

# -----------------------------------------------------------------------------
# Fetch Meme Logic
# -----------------------------------------------------------------------------
def fetch_meme(sort: str = "hot", time_filter: str = "day", limit: int = 50):
    """
    Fetch a meme based on the sort type. For 'random', fetch from the local cache.
    """
    if sort == "random":
        return fetch_meme_from_cache()  # Use the cache for random memes

    subreddit = reddit.subreddit("memes")
    if sort == "hot":
        posts = list(subreddit.hot(limit=limit))
    elif sort == "new":
        posts = list(subreddit.new(limit=limit))
    elif sort == "top":
        posts = list(subreddit.top(time_filter=time_filter, limit=limit))
    else:
        posts = list(subreddit.hot(limit=limit))

    for submission in posts:
        if submission.url.endswith((".jpg", ".jpeg", ".png", ".gif")) and not submission.stickied:
            return (submission.title, submission.url)

    return (None, None)

# -----------------------------------------------------------------------------
# Bot Commands and Callbacks
# -----------------------------------------------------------------------------
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome to Meme Bot! Choose a meme style below."
    )
    await show_main_menu(update.message.chat)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles button presses: "Next Meme" or "Return to Menu".
    """
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "return_menu":
        await show_main_menu(query.message)
        return

    # If callback_data is in the format "sort|time_filter"
    try:
        sort, time_filter = data.split("|")
    except ValueError:
        logging.error("Invalid callback_data format. Expected 'sort|time_filter'.")
        await query.edit_message_text("Error: Invalid button data.")
        return

    # Fetch a meme
    title, url = fetch_meme(sort=sort, time_filter=time_filter)
    if url:
        cb_data = f"{sort}|{time_filter}"
        keyboard = [
            [InlineKeyboardButton("Next Meme", callback_data=cb_data)],
            [InlineKeyboardButton("Return to Menu", callback_data="return_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # If the original message is a photo, edit it
        if query.message.photo:
            new_media = InputMediaPhoto(media=url, caption=title or "Meme")
            try:
                await query.edit_message_media(media=new_media, reply_markup=reply_markup)
            except Exception as e:
                logging.error(f"Failed to edit message media: {e}")
                await query.message.chat.send_photo(photo=url, caption=title, reply_markup=reply_markup)
        else:
            # If the original message is text, delete it and send a new photo
            await query.message.delete()
            await query.message.chat.send_photo(photo=url, caption=title, reply_markup=reply_markup)
    else:
        await query.edit_message_text("No memes available right now!")

async def show_main_menu(chat_or_message):
    """
    Displays the main menu with inline buttons.
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

    if isinstance(chat_or_message, Chat):
        await chat_or_message.send_message("Choose a meme style:", reply_markup=reply_markup)
    elif isinstance(chat_or_message, Message):
        await chat_or_message.delete()
        await chat_or_message.chat.send_message("Choose a meme style:", reply_markup=reply_markup)

# -----------------------------------------------------------------------------
# Main Function
# -----------------------------------------------------------------------------
def main():
    update_meme_cache()  # Populate the cache at startup
    app = ApplicationBuilder().token("7378773393:AAFiwJD2nXX5OO5TJCuJc9QNdNct9jm1AKA").build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling()

if __name__ == "__main__":
    main()