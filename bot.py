import telebot
from telebot import types
from tariffs import tariffs
from keyboards import get_result_keyboard, get_bank_link_keyboard
import os
from flask import Flask, request

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
app = Flask(__name__)
user_data = {}

# === HANDLERS ===
@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_data[message.chat.id] = {}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*tariffs.keys())
    bot.send_message(message.chat.id, "👋 Выбери банк:", reply_markup=markup)

# 🔁 сюда вставь остальные message_handler (банк, ставка, расчёты и т.д.)

# === FLASK ===
@app.route('/', methods=['GET'])
def index():
    return "Bot is running!"

@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Invalid content type', 403

# === WEBHOOK SETUP ===
if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url='https://oplata-chast-bot.onrender.com/')
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
