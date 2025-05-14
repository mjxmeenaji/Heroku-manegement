import os
import logging
import sqlite3
import requests
from io import BytesIO
import zipfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackContext, CallbackQueryHandler

# Logging setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

SUPPORT_GROUP = "https://t.me/SFW_BotCore"
OWNER_ID = 5397621246
DB_NAME = "users.db"

# Initialize DB
with sqlite3.connect(DB_NAME) as conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, api_key TEXT)''')

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
            f'https://api.heroku.com/{endpoint}',
            headers=headers,
            json=data
        )
        return response
    except Exception as e:
        logger.error(f"Heroku API Error: {e}")
        return None

def start(update: Update, context: CallbackContext):
    user = update.effective_user
    help_text = f"""<b>✨ Welcome, {user.first_name}!</b>

I’m a powerful Heroku Manager Bot built to manage your Heroku apps directly from Telegram.

<b>📌 Features:</b>
• /setkey - Save your Heroku API Key
• /apps - List all your Heroku apps
• /download [appname] - Get downloadable tarball as ZIP
• /restart [appname] - Restart any app
• /restart_all - Restart all apps together
• /logs [appname] - View app logs
• /remove_key - Delete your API Key

<b>🛡️ Secure:</b> Your API keys are stored privately.
<b>📞 Support:</b> <a href="{SUPPORT_GROUP}">SFW BotCore</a>
"""
    update.message.reply_text(help_text, parse_mode='HTML', disable_web_page_preview=True)

def set_key(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    api_key = ' '.join(context.args)

    if not api_key:
        update.message.reply_text("❌ Usage: /setkey YOUR_HEROKU_API_KEY")
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
        update.message.reply_text("❌ Please set your API key using /setkey")
        return

    headers = {'Authorization': f'Bearer {api_key}', 'Accept': 'application/vnd.heroku+json; version=3'}

    try:
        response = requests.get('https://api.heroku.com/apps', headers=headers)
        if response.status_code == 200:
            apps = response.json()
            if not apps:
                update.message.reply_text("🚫 No Heroku apps found!")
                return

            keyboard = [[InlineKeyboardButton(app['name'], callback_data=f"app_{app['name']}")] for app in apps]
            reply_markup = InlineKeyboardMarkup(keyboard)
            update.message.reply_text(f"📦 Your Heroku Apps ({len(apps)}):", reply_markup=reply_markup)
        else:
            update.message.reply_text(f"❌ Error: {response.text}")
    except Exception as e:
        update.message.reply_text(f"🔥 API Error: {str(e)}")

def restart_app(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args:
        update.message.reply_text("Usage: /restart [appname]")
        return

    app_name = context.args[0]
    response = heroku_api(user_id, f"apps/{app_name}/dynos", method='DELETE')

    if response and response.status_code == 202:
        update.message.reply_text(f"♻️ Restarted app: {app_name}")
    else:
        update.message.reply_text("❌ Failed to restart app.")

def restart_all(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    api_key = get_heroku_client(user_id)
    if not api_key:
        update.message.reply_text("❌ Set your API key first using /setkey")
        return

    headers = {'Authorization': f'Bearer {api_key}', 'Accept': 'application/vnd.heroku+json; version=3'}
    response = requests.get('https://api.heroku.com/apps', headers=headers)
    if response.status_code == 200:
        count = 0
        for app in response.json():
            heroku_api(user_id, f"apps/{app['name']}/dynos", method="DELETE")
            count += 1
        update.message.reply_text(f"✅ Restarted {count} apps.")
    else:
        update.message.reply_text("❌ Failed to restart apps.")

def get_logs(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args:
        update.message.reply_text("Usage: /logs [appname]")
        return

    app_name = context.args[0]
    response = heroku_api(user_id, f"apps/{app_name}/log-sessions", method='POST', data={"lines": 100})

    if response and response.status_code == 201:
        log_url = response.json()["logplex_url"]
        update.message.reply_text(f"📄 Logs: {log_url}")
    else:
        update.message.reply_text("❌ Failed to get logs.")

def download_backup(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if not context.args:
        update.message.reply_text("Usage: /download [appname]")
        return

    app_name = context.args[0]
    api_key = get_heroku_client(user_id)
    if not api_key:
        update.message.reply_text("❌ Set your API key first using /setkey")
        return

    headers = {
        "Accept": "application/vnd.heroku+json; version=3",
        "Authorization": f"Bearer {api_key}"
    }

    app_info = requests.get(f"https://api.heroku.com/apps/{app_name}/releases", headers=headers)
    if app_info.status_code != 200:
        update.message.reply_text("❌ Failed to fetch release info!")
        return

    releases = app_info.json()
    if not releases:
        update.message.reply_text("❌ No releases found!")
        return

    latest = sorted(releases, key=lambda x: x['version'], reverse=True)[0]
    slug_id = latest.get("slug", {}).get("id")
    if not slug_id:
        update.message.reply_text("❌ Could not find slug for latest release!")
        return

    slug_info = requests.get(f"https://api.heroku.com/apps/{app_name}/slugs/{slug_id}", headers=headers)
    if slug_info.status_code == 200:
        download_url = slug_info.json().get("blob", {}).get("url")

        update.message.reply_text("Downloading slug and creating ZIP file...")
        try:
            response = requests.get(download_url)
            response.raise_for_status()

            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.writestr("app.tar.gz", response.content)
            zip_buffer.seek(0)

            update.message.reply_document(document=zip_buffer, filename="heroku_app.zip", caption="Your slug as ZIP")
        except Exception as e:
            update.message.reply_text(f"Failed to download or zip slug: {e}")
    else:
        update.message.reply_text("❌ Failed to get slug URL!")

def remove_key(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE user_id=?", (user_id,))
    conn.commit()
    conn.close()
    update.message.reply_text("🗑️ API Key removed!")

def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    if query.data.startswith('app_'):
        app_name = query.data.replace('app_', '')
        response = heroku_api(query.from_user.id, f"apps/{app_name}")

        if response and response.status_code == 200:
            app = response.json()
            message = (
                f"*{app['name']}*\n"
                f"🏧 ID: `{app['id']}`\n"
                f"🌍 Web URL: {app.get('web_url', 'N/A')}\n"
                f"⏰ Created: {app['created_at']}\n"
                f"🔄 Updated: {app['updated_at']}"
            )
            query.edit_message_text(text=message, parse_mode='Markdown')
        else:
            query.edit_message_text("❌ Failed to fetch app details!")

def error_handler(update: Update, context: CallbackContext):
    logger.error(f"Error: {context.error}")
    if update and update.effective_message:
        update.effective_message.reply_text(f"⚠️ Error occurred. Contact support: {SUPPORT_GROUP}")

def main():
    TOKEN = os.getenv('TELEGRAM_TOKEN')
    if not TOKEN:
        print("❌ TELEGRAM_TOKEN not set!")
        return

    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("setkey", set_key))
    dp.add_handler(CommandHandler("apps", list_apps))
    dp.add_handler(CommandHandler("restart", restart_app))
    dp.add_handler(CommandHandler("restart_all", restart_all))
    dp.add_handler(CommandHandler("logs", get_logs))
    dp.add_handler(CommandHandler("download", download_backup))
    dp.add_handler(CommandHandler("remove_key", remove_key))
    dp.add_handler(CallbackQueryHandler(button_click))
    dp.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
