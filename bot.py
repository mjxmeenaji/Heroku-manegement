import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
import requests
from uuid import uuid4

# कॉन्फ़िगरेशन
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

SUPPORT_GROUP = "https://t.me/SFW_BotCore"
OWNER_ID = 5397621246
DB_NAME = "users.db"

# डेटाबेस इनिशियलाइज़ करें
with sqlite3.connect(DB_NAME) as conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY, api_key TEXT)''')

def get_db_connection():
    return sqlite3.connect(DB_NAME)

# Heroku API Utilities
def heroku_api(user_id, endpoint, method='GET', data=None):
    api_key = get_heroku_client(user_id)
    if not api_key:
        return None
    
    headers = {
        'Accept': 'application/vnd.heroku+json; version=3',
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.request(
            method, 
            f'https://api.heroku.com/apps/{endpoint}',
            headers=headers,
            json=data
        )
        return response
    except Exception as e:
        logger.error(f"Heroku API Error: {e}")
        return None

# Command Handlers
def restart_app(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args:
        update.message.reply_text("❌ App name required: /restart <app_name>")
        return
    
    app_name = context.args[0]
    response = heroku_api(user_id, f"{app_name}/dynos", 'DELETE')
    
    if response and response.status_code == 202:
        update.message.reply_text(f"♻️ {app_name} restarted successfully!")
    else:
        update.message.reply_text("❌ Failed to restart app!")

def get_logs(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args:
        update.message.reply_text("❌ App name required: /logs <app_name>")
        return
    
    app_name = context.args[0]
    response = heroku_api(user_id, f"{app_name}/log-sessions", 'POST', {'tail': True})
    
    if response and response.status_code == 200:
        log_url = response.json().get('logplex_url')
        update.message.reply_text(f"📜 Logs for {app_name}:\n{log_url}")
    else:
        update.message.reply_text("❌ Failed to fetch logs!")

def download_backup(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args:
        update.message.reply_text("❌ App name required: /download <app_name>")
        return
    
    app_name = context.args[0]
    response = heroku_api(user_id, f"{app_name}/slug", 'GET')
    
    if response and response.status_code == 200:
        download_url = response.json()['blob']['url']
        update.message.reply_text(f"📥 Download {app_name}:\n{download_url}")
    else:
        update.message.reply_text("❌ Failed to get download link!")

def remove_key(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    with get_db_connection() as conn:
        conn.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    update.message.reply_text("🔑 API Key removed successfully!")

def restart_all(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    response = heroku_api(user_id, "dynos", 'DELETE')
    
    if response and response.status_code == 202:
        update.message.reply_text("🚀 All dynos restarted successfully!")
    else:
        update.message.reply_text("❌ Failed to restart all apps!")

# Main Function Updated
def main():
    TOKEN = os.getenv('TELEGRAM_TOKEN')
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    # Register All Commands
    commands = [
        ('start', start),
        ('setkey', set_key),
        ('apps', list_apps),
        ('restart', restart_app),
        ('restart_all', restart_all),
        ('logs', get_logs),
        ('download', download_backup),
        ('remove_key', remove_key)
    ]
    
    for cmd, handler in commands:
        dp.add_handler(CommandHandler(cmd, handler))
    
    dp.add_handler(CallbackQueryHandler(button_click))
    dp.add_error_handler(error_handler)
    
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
