# 🔥 Heroku Management Bot

[![GitHub Stars](https://img.shields.io/github/stars/Akash8t2/Heroku-manegement?style=for-the-badge)](https://github.com/Akash8t2/Heroku-manegement/stargazers)
[![Forks](https://img.shields.io/github/forks/Akash8t2/Heroku-manegement?style=for-the-badge)](https://github.com/Akash8t2/Heroku-manegement/network/members)
[![Issues](https://img.shields.io/github/issues/Akash8t2/Heroku-manegement?style=for-the-badge)](https://github.com/Akash8t2/Heroku-manegement/issues)
[![MIT License](https://img.shields.io/github/license/Akash8t2/Heroku-manegement?style=for-the-badge)](https://github.com/Akash8t2/Heroku-manegement/blob/main/LICENSE)

A powerful Telegram bot 🤖 for managing Heroku apps with advanced features and secure multi-user support.

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy?template=https://github.com/mjxmeenaji/Heroku-manegement)

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
```

### Heroku Deployment
1. Click the [Deploy to Heroku](#) button above
2. Set required environment variables:
   - `TELEGRAM_TOKEN` - From @BotFather
   - `HEROKU_API_KEY` - From Heroku Account Settings
3. Deploy!

## 📋 Configuration

1. Get Telegram Bot Token from [@BotFather](https://t.me/BotFather)
2. Get Heroku API Key from [Account Settings](https://dashboard.heroku.com/account)
3. Add your user ID to `AUTHORIZED_USERS` in config

## 🚀 Usage

| Command               | Description                          | Example                     |
|-----------------------|--------------------------------------|-----------------------------|
| `/start`              | Show welcome message                 | `/start`                    |
| `/setkey <api_key>`   | Store Heroku API key                 | `/setkey 1234-5678-90ab`    |
| `/apps`               | List all Heroku apps                 | `/apps`                     |
| `/restart <app_name>` | Restart specific app dynos           | `/restart my-cool-app`      |
| `/logs <app_name>`    | Get app logs                         | `/logs production-app`      |
| `/download_all`       | Backup all apps                      | `/download_all`             |
| `/remove_key`         | Delete stored API key                | `/remove_key`               |

## 📸 Screenshots

![Main Interface](https://i.imgur.com/5XbJ7dD.png)
![App Management](https://i.imgur.com/9W7RZlB.png)

## 📞 Support

For support/bug reports:
- Join our [Support Group](https://t.me/SFW_BotCore)
- Contact Owner [—͟͟͞͞𝗔𝗞𝗔𝗦𝗛 🥀](https://t.me/botcasx)

## 🤝 Contributing

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.

## 💎 Acknowledgments

- Heroku API Documentation
- python-telegram-bot Team
- Telegram Bot API
