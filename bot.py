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

    # Deployment Flow
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
def cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]])

def branch_keyboard(branches):
    buttons = [[InlineKeyboardButton(branch, callback_data=f"branch_{branch}")] for branch in branches]
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    return InlineKeyboardMarkup(buttons)

# Command Handlers
def start(update: Update, context: CallbackContext):
    user = update.effective_user
    HerokuManager(user.id).init_deployment()
    
    update.message.reply_text(
        "🚀 Heroku Deployment Bot\n"
        "Send your GitHub repository URL:",
        reply_markup=cancel_keyboard()
    )
    log_activity(context, user.__dict__, "Bot Started")

def set_api(update: Update, context: CallbackContext):
    user = update.effective_user
    args = context.args
    
    if not args:
        update.message.reply_text("❌ Usage: /setapi <your_heroku_api_key>")
        return
    
    api_key = args[0]
    headers = {
        'Accept': 'application/vnd.heroku+json; version=3',
        'Authorization': f'Bearer {api_key}'
    }
    
    try:
        response = requests.get('https://api.heroku.com/account', headers=headers)
        if response.status_code != 200:
            update.message.reply_text("❌ Invalid API Key!")
            return
        
        HerokuManager(user.id).set_api_key(api_key)
        update.message.reply_text("✅ API Key Saved Successfully!")
        log_activity(context, user.__dict__, "API Key Updated", f"Key: {api_key[:6]}****")
        
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")

# Message Handlers
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

def handle_branch(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    manager = HerokuManager(user.id)
    
    branch = query.data.split("_")[1]
    manager.save_branch(branch)
    manager.update_step("awaiting_app_name")
    
    query.edit_message_text(
        "🏷️ Enter Heroku App Name (lowercase only):\n"
        "Type /cancel to abort",
        reply_markup=cancel_keyboard()
    )
    log_activity(context, user.__dict__, "Branch Selected", branch)

def handle_app_name(update: Update, context: CallbackContext):
    user = update.effective_user
    manager = HerokuManager(user.id)
    
    app_name = update.message.text.strip().lower()
    if not re.match(r"^[a-z0-9-]{1,30}$", app_name):
        update.message.reply_text("❌ Invalid app name!", reply_markup=cancel_keyboard())
        return
    
    # Check app name availability
    headers = {
        "Accept": "application/vnd.heroku+json; version=3",
        "Authorization": f"Bearer {manager.get_api_key()}"
    }
    
    try:
        response = requests.get(f"https://api.heroku.com/apps/{app_name}", headers=headers)
        
        if response.status_code == 200:
            update.message.reply_text("❌ Name taken! Try another:", reply_markup=cancel_keyboard())
        else:
            manager.save_app_name(app_name)
            manager.update_step("awaiting_vars")
            
            update.message.reply_text(
                "📝 Enter required environment variables (comma separated):\n"
                "Example: BOT_TOKEN,API_KEY,DB_URL",
                reply_markup=cancel_keyboard()
            )
            log_activity(context, user.__dict__, "App Name Set", app_name)
            
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")

def handle_env_vars(update: Update, context: CallbackContext):
    user = update.effective_user
    manager = HerokuManager(user.id)
    
    vars_list = [v.strip() for v in update.message.text.split(",")]
    manager.save_required_vars(vars_list)
    manager.update_step("awaiting_env_values")
    
    update.message.reply_text(
        f"🔑 Provide value for {vars_list[0]}:",
        reply_markup=cancel_keyboard()
    )
    log_activity(context, user.__dict__, "Env Vars Requested", str(vars_list))

def handle_env_value(update: Update, context: CallbackContext):
    user = update.effective_user
    manager = HerokuManager(user.id)
    data = manager.get_deployment_data()
    
    current_var = data["required_vars"][len(manager.get_env_vars())]
    value = update.message.text
    
    manager.add_env_var(current_var, value)
    env_vars = manager.get_env_vars()
    
    if len(env_vars) < len(data["required_vars"]):
        next_var = data["required_vars"][len(env_vars)]
        update.message.reply_text(
            f"✅ {current_var} saved!\n"
            f"Enter value for {next_var}:",
            reply_markup=cancel_keyboard()
        )
    else:
        # Deploy to Heroku
        headers = {
            "Accept": "application/vnd.heroku+json; version=3",
            "Authorization": f"Bearer {manager.get_api_key()}",
            "Content-Type": "application/json"
        }
        
        try:
            # Create app
            response = requests.post(
                "https://api.heroku.com/apps",
                headers=headers,
                json={"name": data["app_name"]}
            )
            
            # Set config vars
            requests.patch(
                f"https://api.heroku.com/apps/{data['app_name']}/config-vars",
                headers=headers,
                json=manager.get_env_vars()
            )
            
            # Trigger deployment
            parts = data["repo_url"].replace("https://github.com/", "").split("/")
            owner, repo = parts[0], parts[1]
            
            requests.post(
                f"https://api.heroku.com/apps/{data['app_name']}/builds",
                headers=headers,
                json={
                    "source_blob": {
                        "url": f"https://github.com/{owner}/{repo}/archive/{data['branch']}.tar.gz"
                    }
                }
            )
            
            update.message.reply_text(
                f"🚀 Deployment Started!\n\n"
                f"App Name: {data['app_name']}\n"
                f"URL: https://{data['app_name']}.herokuapp.com\n"
                f"Dashboard: https://dashboard.heroku.com/apps/{data['app_name']}"
            )
            log_activity(context, user.__dict__, "Deployment Started", str(data))
            
        except Exception as e:
            update.message.reply_text(f"❌ Deployment failed: {str(e)}")
            log_activity(context, user.__dict__, "Deployment Failed", str(e))
        
        manager.reset_deployment()

def cancel(update: Update, context: CallbackContext):
    query = update.callback_query
    user = query.from_user
    HerokuManager(user.id).reset_deployment()
    
    query.edit_message_text("❌ Operation cancelled")
    log_activity(context, user.__dict__, "Operation Cancelled")

def main():
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    
    # Commands
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("setapi", set_api))
    
    # Callbacks
    dp.add_handler(CallbackQueryHandler(handle_branch, pattern="^branch_"))
    dp.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))
    
    # Messages
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_repo))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_app_name))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_env_vars))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_env_value))
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
