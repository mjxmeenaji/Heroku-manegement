import os
import sqlite3
import requests
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Config
SUPPORT_GROUP = "https://t.me/SFW_BotCore"
OWNER_ID = 5397621246
DB_NAME = "users.db"

# Database initialization
with sqlite3.connect(DB_NAME) as conn:
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, api_key TEXT)")

def get_api_key(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT api_key FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def set_api_key(user_id, key):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("INSERT OR REPLACE INTO users (user_id, api_key) VALUES (?, ?)", (user_id, key))
    conn.commit()
    conn.close()

def delete_api_key(user_id):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def validate_heroku_key(api_key):
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/vnd.heroku+json; version=3"}
    try:
        res = requests.get("https://api.heroku.com/account", headers=headers)
        return res.status_code == 200
    except:
        return False

# Bot commands
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    text = f"""
<b>Welcome {user.first_name}!</b>

I'm a Heroku Manager Bot. Use me to manage your Heroku apps.

<b>Commands:</b>
• /setkey - Set your Heroku API Key
• /apps - List all your apps
• /restart <app_name> - Restart app
• /restart_all - Restart all apps
• /logs <app_name> - View logs
• /download <app_name> - Get app tarball URL
• /remove_key - Delete your API key

<a href='{SUPPORT_GROUP}'>Support Group</a> | <a href='tg://user?id={OWNER_ID}'>Owner</a>
"""
    update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)

def setkey(update: Update, context: CallbackContext):
    if not context.args:
        return update.message.reply_text("Usage: /setkey YOUR_HEROKU_API_KEY")
    key = context.args[0]
    if not validate_heroku_key(key):
        return update.message.reply_text("❌ Invalid Heroku API Key!")
    set_api_key(update.effective_user.id, key)
    update.message.reply_text("✅ API Key saved successfully!")

def remove_key(update: Update, context: CallbackContext):
    delete_api_key(update.effective_user.id)
    update.message.reply_text("🗑️ Your Heroku API Key has been deleted.")

def apps(update: Update, context: CallbackContext):
    key = get_api_key(update.effective_user.id)
    if not key:
        return update.message.reply_text("❗ Use /setkey to save your Heroku API key.")
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/vnd.heroku+json; version=3"}
    res = requests.get("https://api.heroku.com/apps", headers=headers)
    if res.status_code != 200:
        return update.message.reply_text("❌ Failed to get apps list.")
    apps = res.json()
    buttons = [[InlineKeyboardButton(app["name"], callback_data=f"app_{app['name']}")] for app in apps]
    markup = InlineKeyboardMarkup(buttons)
    update.message.reply_text("📦 Your Heroku Apps:", reply_markup=markup)

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    app_name = query.data.split("_", 1)[1]
    key = get_api_key(query.from_user.id)
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/vnd.heroku+json; version=3"}
    res = requests.get(f"https://api.heroku.com/apps/{app_name}", headers=headers)
    if res.status_code != 200:
        return query.edit_message_text("❌ Failed to get app details.")
    app = res.json()
    msg = (
        f"<b>📌 App:</b> {app['name']}\n"
        f"🌐 <a href='{app['web_url']}'>Open Web</a>\n"
        f"🕒 Created: {app['created_at'][:10]}\n"
        f"🔁 Updated: {app['updated_at'][:10]}"
    )
    query.edit_message_text(msg, parse_mode="HTML", disable_web_page_preview=True)

def restart(update: Update, context: CallbackContext):
    if not context.args:
        return update.message.reply_text("Usage: /restart <app_name>")
    app_name = context.args[0]
    key = get_api_key(update.effective_user.id)
    if not key:
        return update.message.reply_text("❗ Use /setkey first.")
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/vnd.heroku+json; version=3"}
    res = requests.delete(f"https://api.heroku.com/apps/{app_name}/dynos", headers=headers)
    if res.status_code == 202:
        update.message.reply_text(f"♻️ Restarted app: {app_name}")
    else:
        update.message.reply_text("❌ Failed to restart app.")

def restart_all(update: Update, context: CallbackContext):
    key = get_api_key(update.effective_user.id)
    if not key:
        return update.message.reply_text("❗ Use /setkey first.")
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/vnd.heroku+json; version=3"}
    res = requests.get("https://api.heroku.com/apps", headers=headers)
    if res.status_code != 200:
        return update.message.reply_text("❌ Failed to get app list.")
    apps = res.json()
    count = 0
    for app in apps:
        app_name = app['name']
        requests.delete(f"https://api.heroku.com/apps/{app_name}/dynos", headers=headers)
        count += 1
    update.message.reply_text(f"♻️ Restarted {count} apps!")

def logs(update: Update, context: CallbackContext):
    if not context.args:
        return update.message.reply_text("Usage: /logs <app_name>")
    app_name = context.args[0]
    key = get_api_key(update.effective_user.id)
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/vnd.heroku+json; version=3"}
    res = requests.get(f"https://api.heroku.com/apps/{app_name}/log-sessions", headers=headers, json={"dyno": "web", "lines": 50})
    if res.status_code == 201:
        log_url = res.json()["logplex_url"]
        update.message.reply_text(f"📝 Logs for <b>{app_name}</b>:\n{log_url}", parse_mode="HTML")
    else:
        update.message.reply_text("❌ Failed to fetch logs.")

def download(update: Update, context: CallbackContext):
    if not context.args:
        return update.message.reply_text("Usage: /download <app_name>")
    app_name = context.args[0]
    key = get_api_key(update.effective_user.id)
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/vnd.heroku+json; version=3"}
    res = requests.post(f"https://api.heroku.com/apps/{app_name}/sources", headers=headers)
    if res.status_code == 201:
        url = res.json()["source_blob"]["get_url"]
        update.message.reply_text(f"📦 Download link for <b>{app_name}</b>:\n{url}", parse_mode="HTML")
    else:
        update.message.reply_text("❌ Failed to generate backup.")

def error_handler(update: Update, context: CallbackContext):
    logger.error(msg="Exception while handling update:", exc_info=context.error)
    if update and update.effective_message:
        update.effective_message.reply_text("⚠️ An unexpected error occurred. Please try again later.")

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Register commands
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("setkey", setkey))
    dp.add_handler(CommandHandler("apps", apps))
    dp.add_handler(CommandHandler("restart", restart))
    dp.add_handler(CommandHandler("restart_all", restart_all))
    dp.add_handler(CommandHandler("logs", logs))
    dp.add_handler(CommandHandler("download", download))
    dp.add_handler(CommandHandler("remove_key", remove_key))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
