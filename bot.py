import telebot
from telebot import types
import os
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # не забудь указать его в Render -> Environment
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Данные по процентам
BANK_RATES = {
    "mono": {
        "name": "MonoBank",
        "rates": {
            2: 0.029,
            3: 0.041,
            4: 0.053,
            5: 0.065,
            6: 0.077,
        },
        "markup": 0.013
    },
    "pumb": {
        "name": "ПУМБ",
        "rates": {
            2: 0.026,
            3: 0.039,
            4: 0.049,
            5: 0.06,
            6: 0.072,
        },
        "markup": 0.013
    },
    "privat": {
        "name": "ПриватБанк",
        "rates": {
            2: 0.017,
            3: 0.028,
            4: 0.045,
            5: 0.057,
            6: 0.069,
            7: 0.08
        },
        "markup": 0.013
    }
}

user_data = {}

def calc(bank_key, months, amount):
    rate = BANK_RATES[bank_key]["rates"].get(months)
    markup = BANK_RATES[bank_key]["markup"]
    total_rate = rate + markup
    total_payment = amount * (1 + total_rate)
    monthly_payment = total_payment / (months + 1)  # ← исправлено здесь
    overpay = total_payment - amount
    return {
        "total_payment": round(total_payment, 2),
        "monthly_payment": round(monthly_payment, 2),
        "overpay": round(overpay, 2),
        "rate_percent": round(rate * 100, 1),
        "markup_percent": round(markup * 100, 1),
        "total_percent": round(total_rate * 100, 1)
    }

def get_rate_text(bank_key):
    bank = BANK_RATES[bank_key]
    lines = []
    for months, rate in bank["rates"].items():
        total = round((rate + bank["markup"]) * 100, 1)
        lines.append(f"{months} мес.: {round(rate * 100,1)}% + {round(bank['markup']*100,1)}% = {total}%")
    return "\n".join(lines)

# Старт
@bot.message_handler(commands=["start"])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("MonoBank", callback_data="mono"),
        types.InlineKeyboardButton("PUMB", callback_data="pumb"),
        types.InlineKeyboardButton("ПриватБанк", callback_data="privat")
    )
    bot.send_message(message.chat.id, "🏦 Выберите банк:", reply_markup=markup)

# Выбор банка
@bot.callback_query_handler(func=lambda call: call.data in BANK_RATES)
def choose_bank(call):
    user_id = call.from_user.id
    user_data[user_id] = {"bank": call.data}

    markup = types.InlineKeyboardMarkup()
    for m in BANK_RATES[call.data]["rates"]:
        markup.add(types.InlineKeyboardButton(f"{m} мес", callback_data=f"months_{m}"))

    bot.send_message(call.message.chat.id, "📆 Выберите срок:", reply_markup=markup)

# Выбор срока
@bot.callback_query_handler(func=lambda call: call.data.startswith("months_"))
def choose_months(call):
    user_id = call.from_user.id
    months = int(call.data.split("_")[1])
    user_data[user_id]["months"] = months
    bot.send_message(call.message.chat.id, "💵 Введите сумму к получению:")

# Ввод суммы
@bot.message_handler(func=lambda message: message.chat.id in user_data and "months" in user_data[message.chat.id])
def enter_amount(message):
    user_id = message.chat.id
    try:
        amount = float(message.text.replace(",", "."))
    except:
        bot.send_message(user_id, "❌ Введите сумму цифрами.")
        return

    data = user_data[user_id]
    bank_key = data["bank"]
    months = data["months"]
    calc_data = calc(bank_key, months, amount)

    result = f"""📊 Расчёт по {BANK_RATES[bank_key]["name"]}

Срок: {months} мес. ({months+1} платежей)
Сумма к получению: {amount:.2f} грн
Ставка: {calc_data['rate_percent']}% + {calc_data['markup_percent']}% (эквайринг) = {calc_data['total_percent']}%
Клиент заплатит: {calc_data['total_payment']} грн
Ежемесячно: {calc_data['monthly_payment']} грн
Переплата: {calc_data['overpay']} грн

📈 Тарифы {BANK_RATES[bank_key]["name"]}:
{get_rate_text(bank_key)}
"""

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔁 Изменить банк", callback_data="change_bank"),
        types.InlineKeyboardButton("💸 Изменить сумму", callback_data="change_sum")
    )
    bot.send_message(user_id, result, reply_markup=markup)

# Сброс на выбор банка
@bot.callback_query_handler(func=lambda call: call.data == "change_bank")
def change_bank(call):
    user_id = call.from_user.id
    user_data.pop(user_id, None)

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("MonoBank", callback_data="mono"),
        types.InlineKeyboardButton("PUMB", callback_data="pumb"),
        types.InlineKeyboardButton("ПриватБанк", callback_data="privat")
    )
    bot.send_message(call.message.chat.id, "🏦 Выберите банк:", reply_markup=markup)

# Сброс только суммы
@bot.callback_query_handler(func=lambda call: call.data == "change_sum")
def change_sum(call):
    user_id = call.from_user.id
    if user_id in user_data:
        user_data[user_id].pop("amount", None)
        bot.send_message(call.message.chat.id, "💵 Введите новую сумму к получению:")

# Webhook endpoint
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode("utf-8"))])
    return 'OK', 200

@app.route('/', methods=['GET'])
def index():
    return "✅ Bot is running!"

# Запуск Flask
if __name__ == '__main__':
    import logging
    logging.basicConfig(level=logging.INFO)
    port = int(os.environ.get('PORT', 5000))
    bot.remove_webhook()
    bot.set_webhook(url=f'https://oplata-chast-bot.onrender.com/{TOKEN}')  # замени на своё
    app.run(host='0.0.0.0', port=port)
