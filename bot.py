import logging
import random
import praw
import os
from collections import defaultdict
import time

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
# 1) Logging (for debugging)
# -----------------------------------------------------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# -----------------------------------------------------------------------------
# 2) Credentials (Replace placeholders with your actual tokens/keys)
# -----------------------------------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_SECRET = os.getenv("REDDIT_SECRET")
# Provide a default user agent so it won't fail if the env var isn't set:
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "memesbot by /u/YourRedditUsername")

# -----------------------------------------------------------------------------
# 3) Initialize Reddit (PRAW)
# -----------------------------------------------------------------------------
reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_SECRET,
    user_agent=REDDIT_USER_AGENT
)

# -----------------------------------------------------------------------------
# 4) Helper: Fetch a Meme from r/memes
# -----------------------------------------------------------------------------
class MemeCache:
    def __init__(self, cache_time=3600):  # кеш на 1 час
        self.cache = defaultdict(list)
        self.last_update = defaultdict(float)
        self.cache_time = cache_time

    def needs_update(self, category):
        return time.time() - self.last_update[category] > self.cache_time or not self.cache[category]

    def update_cache(self, category, memes):
        self.cache[category] = memes
        self.last_update[category] = time.time()

    def get_random_meme(self, category):
        if self.cache[category]:
            return random.choice(self.cache[category])
        return None, None

# Создаем глобальный кеш
meme_cache = MemeCache()

async def fetch_meme(sort: str = "hot", time_filter: str = "day", limit: int = 50):
    """Получение мема с использованием кеша"""
    cache_key = f"{sort}_{time_filter}"
    
    try:
        # Проверяем, нужно ли обновить кеш
        if meme_cache.needs_update(cache_key):
            logging.info(f"Обновление кеша для {cache_key}")
            subreddit = reddit.subreddit("memes")
            memes = []

            if sort == "hot":
                posts = list(subreddit.hot(limit=limit))
            elif sort == "new":
                posts = list(subreddit.new(limit=limit))
            elif sort == "top":
                posts = list(subreddit.top(time_filter=time_filter, limit=limit))
            else:
                posts = list(subreddit.hot(limit=limit))

            # Сохраняем все подходящие мемы в кеш
            for post in posts:
                if (post.url.endswith((".jpg", ".jpeg", ".png", ".gif")) 
                    and not post.stickied):
                    memes.append((post.title, post.url))

            meme_cache.update_cache(cache_key, memes)
            logging.info(f"Кеш обновлен для {cache_key}, сохранено {len(memes)} мемов")

        # Получаем случайный мем из кеша
        return meme_cache.get_random_meme(cache_key)

    except Exception as e:
        logging.error(f"Ошибка при получении мема: {e}")
        return None, None

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

    title, meme_url = await fetch_meme(sort=sort, time_filter=time_filter)
    if meme_url:
        cb_data = f"{sort}|{time_filter}"

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
        await show_main_menu(query.message)
        return

    sort, time_filter = data.split("|")
    title, meme_url = await fetch_meme(sort=sort, time_filter=time_filter)
    
    if meme_url:
        cb_data = f"{sort}|{time_filter}"

        keyboard = [
            [InlineKeyboardButton("Next Meme", callback_data=cb_data)],
            [InlineKeyboardButton("Return to Menu", callback_data="return_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if query.message.photo:
            new_media = InputMediaPhoto(media=meme_url, caption=title or "Meme")
            await query.edit_message_media(
                media=new_media,
                reply_markup=reply_markup
            )
        else:
            await query.message.delete()
            await query.message.chat.send_photo(
                photo=meme_url,
                caption=title or "Meme",
                reply_markup=reply_markup
            )
    else:
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