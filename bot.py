import os
import re
import logging
import sqlite3
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    Filters
)

# Setup
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
DB_NAME = "heroku_bot.db"
LOG_GROUP_ID = os.getenv("LOG_GROUP_ID")

# Database Initialization
with sqlite3.connect(DB_NAME) as conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                    (user_id INTEGER PRIMARY KEY,
                     heroku_api_key TEXT)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS deployments 
                    (user_id INTEGER,
                     step TEXT,
                     repo_url TEXT,
                     branch TEXT,
                     app_name TEXT,
                     env_vars TEXT,
                     required_vars TEXT)''')

class HerokuManager:
    def __init__(self, user_id):
        self.user_id = user_id
        self.conn = sqlite3.connect(DB_NAME)
    
    def _execute(self, query, params=()):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        self.conn.commit()
        return cursor

    # API Key Management
    def get_api_key(self):
        cursor = self._execute("SELECT heroku_api_key FROM users WHERE user_id=?", (self.user_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    
    def set_api_key(self, api_key):
        self._execute("INSERT OR REPLACE INTO users (user_id, heroku_api_key) VALUES (?, ?)", 
                     (self.user_id, api_key))

    # Deployment Flow Methods
    def init_deployment(self):
        self._execute("INSERT INTO deployments (user_id) VALUES (?)", (self.user_id,))
    
    def update_step(self, step):
        self._execute("UPDATE deployments SET step=? WHERE user_id=?", (step, self.user_id))
    
    def save_repo(self, repo_url):
        self._execute("UPDATE deployments SET repo_url=? WHERE user_id=?", (repo_url, self.user_id))
    
    def save_branch(self, branch):
        self._execute("UPDATE deployments SET branch=? WHERE user_id=?", (branch, self.user_id))
    
    def save_app_name(self, app_name):
        self._execute("UPDATE deployments SET app_name=? WHERE user_id=?", (app_name, self.user_id))
    
    def save_required_vars(self, vars_list):
        self._execute("UPDATE deployments SET required_vars=? WHERE user_id=?", (','.join(vars_list), self.user_id))
    
    def add_env_var(self, key, value):
        env_vars = self.get_env_vars()
        env_vars[key] = value
        self._execute("UPDATE deployments SET env_vars=? WHERE user_id=?", (str(env_vars), self.user_id))
    
    def get_env_vars(self):
        cursor = self._execute("SELECT env_vars FROM deployments WHERE user_id=?", (self.user_id,))
        result = cursor.fetchone()
        return eval(result[0]) if result and result[0] else {}
    
    def get_deployment_data(self):
        cursor = self._execute("SELECT repo_url, branch, app_name, required_vars FROM deployments WHERE user_id=?", (self.user_id,))
        data = cursor.fetchone()
        return {
            "repo_url": data[0],
            "branch": data[1],
            "app_name": data[2],
            "required_vars": data[3].split(',') if data[3] else []
        } if data else None
    
    def reset_deployment(self):
        self._execute("DELETE FROM deployments WHERE user_id=?", (self.user_id,))

# Activity Logger
def log_activity(context: CallbackContext, user: dict, action: str, details: str = ""):
    log_message = (
        f"🛠️ User Activity Log\n\n"
        f"👤 User: {user['first_name']} (@{user['username']})\n"
        f"🆔 ID: {user['id']}\n"
        f"📝 Action: {action}\n"
        f"🔍 Details: {details}"
    )
    context.bot.send_message(chat_id=LOG_GROUP_ID, text=log_message)

# Keyboard Menus
def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Set API Key", callback_data="set_api"),
         InlineKeyboardButton("📦 My Apps", callback_data="list_apps")],
        [InlineKeyboardButton("❓ Help", callback_data="help"),
         InlineKeyboardButton("🚀 New Deployment", callback_data="new_deploy")]
    ])

def cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])

def branch_keyboard(branches):
    buttons = [[InlineKeyboardButton(branch, callback_data=f"branch_{branch}")] for branch in branches]
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)

# Command Handlers
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    update.message.reply_text(
        "🤖 **Heroku Deployment Manager**\n"
        "Choose an option to get started:",
        reply_markup=main_menu_keyboard(),
        parse_mode='Markdown'
    )
    log_activity(context, user.__dict__, "Bot Started")

# Callback Handlers
def handle_main_menu(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    query.answer()
    
    if query.data == "set_api":
        query.edit_message_text(
            "🔑 Send your Heroku API Key:\n"
            "Get it from https://dashboard.heroku.com/account/applications",
            reply_markup=cancel_keyboard()
        )
        HerokuManager(user.id).update_step("awaiting_api_key")
    
    elif query.data == "list_apps":
        manager = HerokuManager(user.id)
        api_key = manager.get_api_key()
        
        if not api_key:
            query.edit_message_text("❌ API Key not set! Use /start to set it first.")
            return
        
        headers = {
            "Accept": "application/vnd.heroku+json; version=3",
            "Authorization": f"Bearer {api_key}"
        }
        
        try:
            response = requests.get("https://api.heroku.com/apps", headers=headers)
            apps = response.json()
            
            keyboard = [
                [InlineKeyboardButton(app['name'], callback_data=f"app_{app['name']}")]
                for app in apps
            ]
            keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="main_menu")])
            
            query.edit_message_text(
                "📦 Your Heroku Applications:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            log_activity(context, user.__dict__, "App List Viewed")
            
        except Exception as e:
            query.edit_message_text(f"❌ Error: {str(e)}")
    
    elif query.data == "help":
        help_text = (
            "🤖 **Bot Help Guide**\n\n"
            "🔑 *Set API Key* - Store your Heroku API key\n"
            "📦 *My Apps* - List existing applications\n"
            "🚀 *New Deployment* - Deploy new application\n\n"
            "⚙️ *How to Use:*\n"
            "1. Set API key first\n"
            "2. Start new deployment\n"
            "3. Follow step-by-step instructions\n\n"
            "🛠️ Support: @YourSupportChannel"
        )
        query.edit_message_text(help_text, parse_mode='Markdown')
    
    elif query.data == "new_deploy":
        HerokuManager(user.id).init_deployment()
        query.edit_message_text(
            "📥 Send GitHub repository URL:",
            reply_markup=cancel_keyboard()
        )
        log_activity(context, user.__dict__, "New Deployment Started")

# Message Handlers
def handle_api_key(update: Update, context: CallbackContext):
    user = update.effective_user
    manager = HerokuManager(user.id)
    api_key = update.message.text.strip()
    
    headers = {
        'Accept': 'application/vnd.heroku+json; version=3',
        'Authorization': f'Bearer {api_key}'
    }
    
    try:
        response = requests.get('https://api.heroku.com/account', headers=headers)
        if response.status_code != 200:
            update.message.reply_text("❌ Invalid API Key! Try again:")
            return
        
        manager.set_api_key(api_key)
        update.message.reply_text(
            "✅ API Key Verified & Saved!",
            reply_markup=main_menu_keyboard()
        )
        log_activity(context, user.__dict__, "API Key Set", f"Key: {api_key[:6]}****")
        
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")

def handle_repo(update: Update, context: CallbackContext):
    user = update.effective_user
    manager = HerokuManager(user.id)
    
    repo_url = update.message.text
    if not re.match(r"^https?://github.com/[a-zA-Z0-9_-]+/[a-zA-Z0-9_-]+/?$", repo_url):
        update.message.reply_text("❌ Invalid GitHub URL!", reply_markup=cancel_keyboard())
        return
    
    # Get branches
    parts = repo_url.replace("https://github.com/", "").split("/")
    owner, repo = parts[0], parts[1].replace(".git", "")
    
    try:
        response = requests.get(f"https://api.github.com/repos/{owner}/{repo}/branches")
        branches = [b['name'] for b in response.json()]
        
        manager.save_repo(repo_url)
        manager.update_step("awaiting_branch")
        
        update.message.reply_text(
            "🌿 Select a branch:",
            reply_markup=branch_keyboard(branches)
        )
        log_activity(context, user.__dict__, "Repo Received", repo_url)
        
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")

# ... (Previous deployment flow handlers remain same as last code)

def cancel(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    HerokuManager(user.id).reset_deployment()
    
    query.edit_message_text(
        "❌ Operation cancelled",
        reply_markup=main_menu_keyboard()
    )
    log_activity(context, user.__dict__, "Operation Cancelled")

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    
    # Commands
    dp.add_handler(CommandHandler("start", start))
    
    # Callbacks
    dp.add_handler(CallbackQueryHandler(handle_main_menu, pattern="^(set_api|list_apps|help|new_deploy)$"))
    dp.add_handler(CallbackQueryHandler(handle_branch, pattern="^branch_"))
    dp.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))
    
    # Messages
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command & Filters.regex(r'^heroku_.+'), handle_api_key)
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_repo))
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
