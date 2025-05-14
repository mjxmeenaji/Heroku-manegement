# 🔥 Heroku Management Bot

[![GitHub Stars](https://img.shields.io/github/stars/Akash8t2/Heroku-manegement?style=for-the-badge)](https://github.com/Akash8t2/Heroku-manegement/stargazers)
[![Forks](https://img.shields.io/github/forks/Akash8t2/Heroku-manegement?style=for-the-badge)](https://github.com/Akash8t2/Heroku-manegement/network/members)
[![Issues](https://img.shields.io/github/issues/Akash8t2/Heroku-manegement?style=for-the-badge)](https://github.com/Akash8t2/Heroku-manegement/issues)
[![MIT License](https://img.shields.io/github/license/Akash8t2/Heroku-manegement?style=for-the-badge)](https://github.com/Akash8t2/Heroku-manegement/blob/main/LICENSE)

A powerful Telegram bot 🤖 for managing Heroku apps with advanced features and secure multi-user support.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/Akash8t2/Heroku-manegement)

## 🌟 Features

- 🔑 Multi-user API Key Management
- 📥 App Backup & Download
- ♻️ Dyno Restart System
- 📜 Real-time Log Access
- 🛡️ Secure SQLite Database
- 📱 Interactive Inline Buttons
- ⚡ Quick Commands
- 📊 App Statistics

## 🛠️ Technologies Used

- Python 3.9+
- python-telegram-bot
- Heroku API
- SQLite Database
- Requests Library

## ⚙️ Installation

### Local Setup
```bash
git clone https://github.com/Akash8t2/Heroku-manegement.git
cd Heroku-manegement
pip install -r requirements.txt

# Set environment variables
export TELEGRAM_TOKEN="your_bot_token"
export HEROKU_API_KEY="your_heroku_key"

python bot.py
