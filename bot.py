import telebot
from telebot import types
from tariffs import tariffs
from keyboards import get_result_keyboard, get_bank_link_keyboard
import os

bot = telebot.TeleBot(os.getenv("TELEGRAM_BOT_TOKEN"))
user_data = {}

@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_data[message.chat.id] = {}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*tariffs.keys())
    bot.send_message(message.chat.id, "👋 Выбери банк:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in tariffs)
def choose_bank(message):
    user_data[message.chat.id] = {"bank": message.text}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*[str(k) for k in tariffs[message.text].keys()])
    bot.send_message(message.chat.id, "📅 Выбери количество месяцев:", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text.isdigit())
def handle_numbers(message):
    chat_id = message.chat.id
    user = user_data.get(chat_id, {})
    if "bank" in user and "months" not in user:
        months = int(message.text)
        if months not in tariffs[user["bank"]]:
            bot.send_message(chat_id, "❌ Неверный срок.")
            return
        user_data[chat_id]["months"] = months
        bot.send_message(chat_id, "💵 Введи сумму, которую ты хочешь получить:", reply_markup=types.ReplyKeyboardRemove())
    elif "months" in user:
        try:
            amount = float(message.text)
        except ValueError:
            bot.send_message(chat_id, "❌ Введи корректную сумму.")
            return

        bank = user["bank"]
        months = user["months"]
        base_rate = tariffs[bank][months]
        extra_rate = 0.013 if bank == "ПриватБанк" else 0.0
        total_rate = base_rate + extra_rate

        total = amount / (1 - total_rate)
        monthly = total / (months + 1)
        overpay = total - amount

        user_data[chat_id]["amount"] = amount

        # Формирование строки со ставкой
        if extra_rate > 0:
            rate_str = f"{base_rate * 100:.1f}% + {extra_rate * 100:.1f}% (эквайринг) = {total_rate * 100:.1f}%"
        else:
            rate_str = f"{total_rate * 100:.1f}%"

        # Таблица тарифов
        if extra_rate > 0:
            rate_table = "\n".join([
                f"<b>{m} мес.</b>: {int(r * 1000)/10:.1f}% + {int(extra_rate * 1000)/10:.1f}% = {int((r + extra_rate) * 1000)/10:.1f}%"
                for m, r in sorted(tariffs[bank].items())
            ])
        else:
            rate_table = "\n".join([
                f"<b>{m} мес.</b>: {int(r * 1000)/10:.1f}%"
                for m, r in sorted(tariffs[bank].items())
            ])

        text = (
            f"📊 <b>Расчёт по {bank}</b>\n\n"
            f"<b>Срок:</b> {months} мес. ({months + 1} платежей)\n"
            f"<b>Сумма к получению:</b> {amount:.2f} грн\n"
            f"<b>Ставка:</b> {rate_str}\n"
            f"<b>Клиент заплатит:</b> {total:.2f} грн\n"
            f"<b>Ежемесячно:</b> {monthly:.2f} грн\n"
            f"<b>Переплата:</b> {overpay:.2f} грн\n\n"
            f"📈 <b>Тарифы {bank}:</b>\n{rate_table}"
        )

        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=get_result_keyboard())

        link_kb = get_bank_link_keyboard(bank)
        if link_kb:
            bot.send_message(chat_id, "⬇️ Перейти в бот для оформления:", reply_markup=link_kb)

@bot.message_handler(func=lambda msg: msg.text in ["🔁 Изменить банк", "📅 Изменить срок", "💵 Изменить сумму", "🆕 Начать сначала"])
def handle_change(message):
    chat_id = message.chat.id
    action = message.text
    if action == "🔁 Изменить банк" or action == "🆕 Начать сначала":
        user_data[chat_id] = {}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(*tariffs.keys())
        bot.send_message(chat_id, "Выбери банк:", reply_markup=markup)
    elif action == "📅 Изменить срок":
        bank = user_data[chat_id].get("bank")
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(*[str(k) for k in tariffs[bank].keys()])
        bot.send_message(chat_id, "Выбери количество месяцев:", reply_markup=markup)
    elif action == "💵 Изменить сумму":
        user_data[chat_id].pop("amount", None)
        bot.send_message(chat_id, "Введи сумму, которую ты хочешь получить:", reply_markup=types.ReplyKeyboardRemove())

import threading
import time
import flask

# Запускаем polling в потоке
def run_bot():
    bot.polling(none_stop=True)

threading.Thread(target=run_bot).start()

# Фейковый web-сервер
app = flask.Flask(__name__)

@app.route('/')
def index():
    return "Bot is running"

# Render требует, чтобы процесс слушал порт
if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
bot.polling()
