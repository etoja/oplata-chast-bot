import telebot
from telebot import types
from flask import Flask, request
import os

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')  # Установи переменную окружения на Render
bot = telebot.TeleBot(TOKEN)
APP_URL = 'https://oplata-chast-bot.onrender.com/'  # твой URL
WEBHOOK_PATH = f'/{TOKEN}'
WEBHOOK_URL = APP_URL + WEBHOOK_PATH

app = Flask(__name__)

BANKS = {
    'mono': {
        'name': 'MonoBank',
        'rates': {
            2: 0.03,
            3: 0.04,
            4: 0.05,
            5: 0.06,
            6: 0.07,
        },
    },
    'pumb': {
        'name': 'PUMB',
        'rates': {
            2: 0.03,
            3: 0.045,
            4: 0.06,
            5: 0.075,
            6: 0.09,
        },
    },
    'privat': {
        'name': 'PrivatBank',
        'rates': {
            2: 0.017,
            3: 0.028,
            4: 0.045,
            5: 0.057,
            6: 0.069,
            7: 0.080,
        },
        'extra_fee': 0.013  # эквайринг
    },
}


def calculate(bank_key, months, desired_amount):
    bank = BANKS[bank_key]
    base_rate = bank['rates'].get(months)
    if base_rate is None:
        return f"⛔️ Для {months} месяцев нет данных по ставке."
    
    extra_fee = bank.get('extra_fee', 0)
    total_rate = base_rate + extra_fee

    amount_to_client = desired_amount / (1 - total_rate)
    monthly_payment = amount_to_client / (months + 1)
    overpay = amount_to_client - desired_amount

    result = f"📊 Расчёт по {bank['name']}\n\n"
    result += f"Срок: {months} мес. ({months+1} платежей)\n"
    result += f"Сумма к получению: {desired_amount:.2f} грн\n"

    if extra_fee:
        result += f"Ставка: {base_rate*100:.1f}% + {extra_fee*100:.1f}% (эквайринг) = {total_rate*100:.1f}%\n"
    else:
        result += f"Ставка: {total_rate*100:.1f}%\n"

    result += f"Клиент заплатит: {amount_to_client:.2f} грн\n"
    result += f"Ежемесячно: {monthly_payment:.2f} грн\n"
    result += f"Переплата: {overpay:.2f} грн\n\n"

    result += f"📈 Тарифы {bank['name']}:\n"
    for m, rate in bank['rates'].items():
        full_rate = rate + bank.get('extra_fee', 0)
        if bank_key == 'privat':
            result += f"{m} мес.: {rate*100:.1f}% + {bank['extra_fee']*100:.1f}% = {full_rate*100:.1f}%\n"
        else:
            result += f"{m} мес.: {full_rate*100:.1f}%\n"
    return result


@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row('Mono', 'PUMB', 'Privat')
    bot.send_message(message.chat.id, "Выберите банк:", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text.lower() in ['mono', 'pumb', 'privat'])
def choose_bank(message):
    bank = message.text.lower()
    bot.send_message(message.chat.id, f"Введите срок в месяцах для {bank.title()}:")
    bot.register_next_step_handler(message, ask_months, bank)


def ask_months(message, bank):
    try:
        months = int(message.text)
        bot.send_message(message.chat.id, "Введите сумму, которую вы хотите получить на руки:")
        bot.register_next_step_handler(message, show_result, bank, months)
    except:
        bot.send_message(message.chat.id, "Введите корректное число месяцев.")


def show_result(message, bank, months):
    try:
        amount = float(message.text)
        result = calculate(bank, months, amount)
        bot.send_message(message.chat.id, result)
    except:
        bot.send_message(message.chat.id, "Введите корректную сумму.")


@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Invalid request', 403


@app.route('/', methods=['GET'])
def index():
    return 'Бот работает'


if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
