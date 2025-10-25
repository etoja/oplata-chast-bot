import telebot
import os
from flask import Flask, request

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

BANK_RATES = {
    "mono": {
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        6: 0,
        7: 0
    },
    "pumb": {
        2: 0,
        3: 0,
        4: 0,
        5: 0,
        6: 0,
        7: 0
    },
    "privat": {
        2: 1.7,
        3: 2.8,
        4: 4.5,
        5: 5.7,
        6: 6.9,
        7: 8.0
    }
}

EXTRA_PERCENT_PRIVAT = 1.3  # Эквайринг

@app.route('/', methods=['GET', 'HEAD'])
def index():
    return 'OK'

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return 'ok'

@bot.message_handler(commands=['start'])
def send_welcome(message):
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("mono", "pumb", "privat")
    bot.send_message(
        message.chat.id,
        "👋 Привет! Выбери банк или введи вручную в формате:\n\n<банк> <срок в месяцах> <сумма>\n\nПример:\nmono 3 1000\n\nДоступные банки: mono, pumb, privat",
        reply_markup=markup
    )

@bot.message_handler(func=lambda message: True)
def handle_input(message):
    try:
        parts = message.text.lower().split()
        if len(parts) == 1 and parts[0] in BANK_RATES:
            bank = parts[0]
            rates = BANK_RATES[bank]
            response = f"📈 Тарифы {bank.title()}:\n"
            for months, rate in rates.items():
                if bank == "privat":
                    total = rate + EXTRA_PERCENT_PRIVAT
                    response += f"{months} мес.: {total:.1f}% ({rate:.1f}% + {EXTRA_PERCENT_PRIVAT:.1f}% эквайринг)\n"
                else:
                    response += f"{months} мес.: {rate:.1f}%\n"
            bot.send_message(message.chat.id, response)
            return

        bank, term_str, amount_str = parts
        term = int(term_str)
        amount = float(amount_str)
        rates = BANK_RATES.get(bank)
        if not rates or term not in rates:
            bot.send_message(message.chat.id, "❌ Неверные данные. Проверь банк и срок.")
            return

        base_rate = rates[term]
        final_rate = base_rate
        if bank == "privat":
            final_rate += EXTRA_PERCENT_PRIVAT

        client_pays = amount / (1 - final_rate / 100)
        monthly_payment = client_pays / (term + 1)
        overpay = client_pays - amount

        response = f"📊 Расчёт по {bank.title()}\n\n"
        response += f"Срок: {term} мес. ({term + 1} платежей)\n"
        if bank == "privat":
            response += f"Ставка: {base_rate:.1f}% + {EXTRA_PERCENT_PRIVAT:.1f}% (эквайринг) = {final_rate:.1f}%\n"
        else:
            response += f"Ставка: {final_rate:.1f}%\n"
        response += f"Сумма к получению: {amount:.2f} грн\n"
        response += f"Клиент заплатит: {client_pays:.2f} грн\n"
        response += f"Ежемесячно: {monthly_payment:.2f} грн\n"
        response += f"Переплата: {overpay:.2f} грн"

        bot.send_message(message.chat.id, response)

    except Exception as e:
        bot.send_message(message.chat.id, "⚠️ Ошибка ввода. Используй формат:\nmono 3 1000")

# Webhook setup (важно для Render)
WEBHOOK_URL = f"https://oplata-chast-bot.onrender.com/{TOKEN}"
bot.remove_webhook()
bot.set_webhook(url=WEBHOOK_URL)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
