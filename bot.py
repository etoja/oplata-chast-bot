import os
from flask import Flask, request
import telebot
from telebot import types
from math import ceil

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN not set")

bot = telebot.TeleBot(TOKEN)
server = Flask(__name__)

user_data = {}

BANK_RATES = {
    'mono': {
        'name': 'MonoBank',
        'rates': {2: 1.5, 3: 2.5, 4: 4.0, 5: 5.2, 6: 6.3, 7: 7.5},
    },
    'pumb': {
        'name': 'PUMB',
        'rates': {2: 1.6, 3: 2.6, 4: 4.2, 5: 5.3, 6: 6.5, 7: 7.6},
    },
    'privat': {
        'name': 'ПриватБанк',
        'rates': {2: 1.7, 3: 2.8, 4: 4.5, 5: 5.7, 6: 6.9, 7: 8.0},
        'acquiring': 1.3
    },
}


def calculate(bank_key, months, amount):
    bank = BANK_RATES[bank_key]
    base_rate = bank['rates'].get(months, 0)
    acquiring = bank.get('acquiring', 0)
    total_rate = base_rate + acquiring

    total_payment = amount / (1 - total_rate / 100)
    monthly = ceil((total_payment / (months + 1)) * 100) / 100
    overpayment = total_payment - amount

    result = f"📊 Расчёт по {bank['name']}\n\n"
    result += f"Срок: {months} мес. ({months + 1} платежей)\n"
    result += f"Сумма к получению: {amount:.2f} грн\n"
    if acquiring:
        result += f"Ставка: {base_rate:.1f}% + {acquiring:.1f}% (эквайринг) = {total_rate:.1f}%\n"
    else:
        result += f"Ставка: {base_rate:.1f}%\n"
    result += f"Клиент заплатит: {total_payment:.2f} грн\n"
    result += f"Ежемесячно: {monthly:.2f} грн\n"
    result += f"Переплата: {overpayment:.2f} грн\n\n"
    result += f"📈 Тарифы {bank['name']}:\n"

    for m, rate in bank['rates'].items():
        r = rate + acquiring if acquiring else rate
        if acquiring:
            result += f"{m} мес.: {rate:.1f}% + {acquiring:.1f}% = {r:.1f}%\n"
        else:
            result += f"{m} мес.: {r:.1f}%\n"

    return result


@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = types.InlineKeyboardMarkup()
    for bank in BANK_RATES:
        btn = types.InlineKeyboardButton(BANK_RATES[bank]['name'], callback_data=f"bank_{bank}")
        markup.add(btn)
    bot.send_message(message.chat.id, "👋 Привет! Выберите банк:", reply_markup=markup)


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    if call.data.startswith("bank_"):
        bank = call.data.split("_")[1]
        user_data[chat_id] = {'bank': bank}

        markup = types.InlineKeyboardMarkup()
        for m in range(2, 8):
            btn = types.InlineKeyboardButton(f"{m} мес.", callback_data=f"term_{m}")
            markup.add(btn)
        bot.edit_message_text(chat_id=chat_id, message_id=call.message.message_id, text="📆 Выберите срок:", reply_markup=markup)

    elif call.data.startswith("term_"):
        term = int(call.data.split("_")[1])
        user_data[chat_id]['term'] = term
        bot.send_message(chat_id, "💰 Введите сумму, которую вы хотите получить:")

    elif call.data == "start_over":
        send_welcome(call.message)


@bot.message_handler(func=lambda message: message.chat.id in user_data and 'term' in user_data[message.chat.id])
def handle_amount(message):
    chat_id = message.chat.id
    try:
        amount = float(message.text)
    except ValueError:
        bot.send_message(chat_id, "🚫 Введите сумму цифрами, например: 1000")
        return

    user_data[chat_id]['amount'] = amount
    data = user_data[chat_id]
    text = calculate(data['bank'], data['term'], data['amount'])

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔁 Изменить банк", callback_data="bank_" + data['bank']),
        types.InlineKeyboardButton("🔄 Сбросить", callback_data="start_over"),
    )

    bot.send_message(chat_id, text, reply_markup=markup)
    user_data.pop(chat_id)


# ---------------- FLASK WEBHOOK SETUP ---------------- #

@server.route(f"/{TOKEN}", methods=['POST'])
def receive_update():
    json_str = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200


@server.route("/", methods=['GET'])
def index():
    return "Bot is running", 200


if __name__ == "__main__":
    # Убираем polling — Render требует web-сервис
    bot.remove_webhook()
    bot.set_webhook(url=f"https://oplata-chast-bot.onrender.com/{TOKEN}")
    port = int(os.environ.get("PORT", 10000))
    server.run(host="0.0.0.0", port=port)
