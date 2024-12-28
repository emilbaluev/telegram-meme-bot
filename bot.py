import logging
import random
import praw
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# Global Variables
meme_cache = []  # Cache for storing fetched memes
seen_memes = {}  # Dictionary to track seen memes for each user

# Reddit Setup
reddit = praw.Reddit(
    client_id="YOUR_CLIENT_ID",
    client_secret="YOUR_CLIENT_SECRET",
    user_agent="meme_bot"
)

def refill_meme_cache(limit=20):
    """
    Fetch memes from r/memes and store them in a global cache.
    """
    global meme_cache
    subreddit = reddit.subreddit("memes")
    posts = subreddit.hot(limit=limit)

    meme_cache = [
        (submission.title, submission.url, submission.id)
        for submission in posts
        if submission.url.endswith((".jpg", ".jpeg", ".png", ".gif")) and not submission.stickied
    ]
    random.shuffle(meme_cache)  # Shuffle memes for variety

def get_next_meme(user_id):
    """
    Fetch the next meme for a user, ensuring it's unseen.
    """
    global meme_cache

    if user_id not in seen_memes:
        seen_memes[user_id] = set()

    if not meme_cache:
        refill_meme_cache(limit=20)

    while meme_cache:
        title, url, submission_id = meme_cache.pop(0)
        if submission_id not in seen_memes[user_id]:
            seen_memes[user_id].add(submission_id)
            return title, url

    return None, None

async def new_meme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Respond to /newmeme by sending a new meme to the user.
    """
    user_id = update.effective_user.id
    title, meme_url = get_next_meme(user_id)

    if not meme_url:
        await update.message.reply_text("No new memes available right now!")
        return

    keyboard = [
        [InlineKeyboardButton("Next Meme", callback_data="new|day")],
        [InlineKeyboardButton("Return to Menu", callback_data="return_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_photo(
        photo=meme_url,
        caption=title or "Meme",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle button clicks for next meme or returning to menu.
    """
    query = update.callback_query
    await query.answer()

    data = query.data
    if data == "return_menu":
        await query.message.reply_text("Returning to main menu!")
        return

    user_id = query.from_user.id
    title, meme_url = get_next_meme(user_id)

    if not meme_url:
        await query.edit_message_text("No new memes available right now!")
        return

    keyboard = [
        [InlineKeyboardButton("Next Meme", callback_data="new|day")],
        [InlineKeyboardButton("Return to Menu", callback_data="return_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.edit_caption(
        caption=title or "Meme",
        reply_markup=reply_markup
    )

def main():
    app = ApplicationBuilder().token("YOUR_TELEGRAM_BOT_TOKEN").build()
    app.add_handler(CommandHandler("newmeme", new_meme_command))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.run_polling()

if __name__ == "__main__":
    main()