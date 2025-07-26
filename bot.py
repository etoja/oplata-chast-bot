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
        amount = float(message.text)
        bank = user["bank"]
        months = user["months"]
        rate = tariffs[bank][months]
        total = amount * (1 + rate)
        monthly = total / (months + 1)
        overpay = total - amount

        user_data[chat_id]["amount"] = amount

        rate_table = "\n".join([f"{m} мес. — {int(r * 1000)/10:.1f}%" for m, r in sorted(tariffs[bank].items())])
        text = (
            f"📊 <b>Расчёт по {bank}</b>\n"
            f"\n"
            f"— <b>Срок:</b> {months} мес. ({months + 1} платежей)\n"
            f"— <b>Сумма к получению:</b> {amount:.2f} грн\n"
            f"— <b>Ставка:</b> {rate*100:.1f}%\n"
            f"— <b>Клиент заплатит:</b> {total:.2f} грн\n"
            f"— <b>Ежемесячно:</b> {monthly:.2f} грн\n"
            f"— <b>Переплата:</b> {overpay:.2f} грн\n\n"
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
        bot.send_message(chat_id, "Введи сумму:", reply_markup=types.ReplyKeyboardRemove())

bot.polling()
