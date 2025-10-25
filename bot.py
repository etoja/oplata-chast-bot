import telebot
from telebot import types
from tariffs import tariffs
from keyboards import get_result_keyboard, get_bank_link_keyboard
import os
import threading
from flask import Flask

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
user_data = {}

# === HANDLERS ===
@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_data[message.chat.id] = {}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*tariffs.keys())
    bot.send_message(message.chat.id, "👋 Выбери банк:", reply_markup=markup)

# (весь твой остальной код тут остаётся без изменений — choose_bank, handle_numbers, handle_change и т.д.)

# === Flask "заглушка" для Render ===
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running"

# === Старт бота в отдельном потоке ===
def run_bot():
    print("🚀 Starting bot polling...")
    bot.polling(none_stop=True)

if __name__ == '__main__':
    threading.Thread(target=run_bot).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
