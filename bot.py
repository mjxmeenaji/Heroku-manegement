import os
import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler
import requests

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

def get_heroku_client(user_id):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT api_key FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

def validate_heroku_key(api_key):
    headers = {
        'Accept': 'application/vnd.heroku+json; version=3',
        'Authorization': f'Bearer {api_key}'
    }
    try:
        response = requests.get('https://api.heroku.com/account', headers=headers)
        return response.status_code == 200
    except:
        return False

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
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    help_text = f"""
    🌟 **Welcome {user.first_name}!** 🌟

    📖 **How to use me:**
    1. /setkey - Add Heroku API Key
    2. /apps - List your Heroku apps
    3. /download [app_name] - Get app tarball
    4. /download_all - Backup all apps
    5. /restart [app_name] - Restart dynos
    6. /restart_all - Nuclear restart
    7. /logs [app_name] - Get app logs
    8. /remove_key - Delete stored API Key

    🔧 Support: {SUPPORT_GROUP}
    👨💻 Owner: <a href='tg://user?id={OWNER_ID}'>Contact</a>
    """
    update.message.reply_text(help_text, parse_mode='HTML', disable_web_page_preview=True)

def set_key(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    api_key = ' '.join(context.args)
    
    if not api_key:
        update.message.reply_text("❌ Please provide API key: /setkey YOUR_HEROKU_API_KEY")
        return
    
    if not validate_heroku_key(api_key):
        update.message.reply_text("❌ Invalid Heroku API Key!")
        return
    
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, api_key) VALUES (?, ?)", (user_id, api_key))
    conn.commit()
    conn.close()
    
    update.message.reply_text("✅ API Key Saved Successfully!")

def list_apps(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    api_key = get_heroku_client(user_id)
    
    if not api_key:
        update.message.reply_text("❌ First set your API key using /setkey")
        return
    
    headers = {'Authorization': f'Bearer {api_key}', 'Accept': 'application/vnd.heroku+json; version=3'}
    
    try:
        response = requests.get('https://api.heroku.com/apps', headers=headers)
        if response.status_code == 200:
            apps = response.json()
            keyboard = [[InlineKeyboardButton(app['name'], callback_data=f"app_{app['id']}")] for app in apps]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(f"📦 Your Heroku Apps ({len(apps)}):", reply_markup=reply_markup)
        else:
            update.message.reply_text(f"❌ Error: {response.text}")
    except Exception as e:
        update.message.reply_text(f"🔥 API Error: {str(e)}")

def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    if query.data.startswith('app_'):
        app_id = query.data.split('_')[1]
        response = heroku_api(query.from_user.id, app_id)
        
        if response and response.status_code == 200:
            app = response.json()
            message = (
                f"📌 **{app['name']}**\n"
                f"🆔 ID: `{app['id']}`\n"
                f"🌍 Web URL: {app['web_url']}\n"
                f"⏰ Created: {app['created_at']}\n"
                f"🔄 Updated: {app['updated_at']}"
            )
            query.edit_message_text(text=message, parse_mode='Markdown')
        else:
            query.edit_message_text("❌ Failed to fetch app details!")

def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Error: {context.error}")
    if update.effective_user:
        update.message.reply_text(f"⚠️ Error: {context.error}\n\nReport to {SUPPORT_GROUP}")

# ... (rest of the command handlers as before)

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
