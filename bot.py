import telebot
from telebot import types
from flask import Flask, request
import os

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')  # переменная окружения
bot = telebot.TeleBot(TOKEN)
APP_URL = 'https://oplata-chast-bot.onrender.com/'
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
        'extra_fee': 0.013
    },
}

user_data = {}

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
    result += f"Срок: {months} мес. ({months + 1} платежей)\n"
    result += f"Сумма к получению: {desired_amount:.2f} грн\n"

    if extra_fee:
        result += f"Ставка: {base_rate * 100:.1f}% + {extra_fee * 100:.1f}% (эквайринг) = {total_rate * 100:.1f}%\n"
    else:
        result += f"Ставка: {total_rate * 100:.1f}%\n"

    result += f"Клиент заплатит: {amount_to_client:.2f} грн\n"
    result += f"Ежемесячно: {monthly_payment:.2f} грн\n"
    result += f"Переплата: {overpay:.2f} грн\n"

    return result

@bot.message_handler(commands=['start'])
def start(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("MonoBank", callback_data='bank_mono'))
    markup.add(types.InlineKeyboardButton("PUMB", callback_data='bank_pumb'))
    markup.add(types.InlineKeyboardButton("PrivatBank", callback_data='bank_privat'))
    bot.send_message(message.chat.id, "Выберите банк:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('bank_'))
def choose_bank(call):
    bank = call.data.split('_')[1]
    user_data[call.from_user.id] = {'bank': bank}
    markup = types.InlineKeyboardMarkup()
    for m in BANKS[bank]['rates'].keys():
        markup.add(types.InlineKeyboardButton(f"{m} мес", callback_data=f'month_{m}'))
    bot.edit_message_text("Выберите срок:", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('month_'))
def choose_month(call):
    months = int(call.data.split('_')[1])
    user_data[call.from_user.id]['months'] = months
    bot.send_message(call.message.chat.id, "Введите сумму, которую хотите получить:")
    bot.register_next_step_handler(call.message, handle_amount)

def handle_amount(message):
    try:
        amount = float(message.text)
        uid = message.from_user.id
        bank = user_data[uid]['bank']
        months = user_data[uid]['months']
        result = calculate(bank, months, amount)
        bot.send_message(message.chat.id, result)
    except:
        bot.send_message(message.chat.id, "Ошибка. Введите корректную сумму.")

@app.route(WEBHOOK_PATH, methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
        bot.process_new_updates([update])
        return '', 200
    return 'invalid request', 403

@app.route('/')
def index():
    return 'Бот работает!'

if __name__ == '__main__':
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 10000)))
