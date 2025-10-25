import telebot
from telebot import types

TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
bot = telebot.TeleBot(TOKEN)

# Проценты банков
TARIFFS = {
    'mono': {2: 0.019, 3: 0.029, 4: 0.038, 5: 0.049, 6: 0.059, 7: 0.068},
    'pumb': {2: 0.019, 3: 0.029, 4: 0.039, 5: 0.049, 6: 0.059, 7: 0.069},
    'privat': {2: 0.017, 3: 0.028, 4: 0.045, 5: 0.057, 6: 0.069, 7: 0.080},
}
EXTRA_PRIVAT = 0.013

selected = {}

@bot.message_handler(commands=['start'])
def start(message):
    selected[message.chat.id] = {'bank': None, 'months': None, 'amount': None}
    markup = types.InlineKeyboardMarkup()
    for bank in ['mono', 'pumb', 'privat']:
        markup.add(types.InlineKeyboardButton(bank.upper(), callback_data=f"bank:{bank}"))
    bot.send_message(message.chat.id, "Выберите банк:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    if call.data.startswith("bank:"):
        bank = call.data.split(":")[1]
        selected[chat_id]['bank'] = bank
        markup = types.InlineKeyboardMarkup()
        for m in [2,3,4,5,6,7]:
            markup.add(types.InlineKeyboardButton(f"{m} мес.", callback_data=f"months:{m}"))
        bot.edit_message_text("Выберите срок:", chat_id=chat_id, message_id=call.message.message_id, reply_markup=markup)

    elif call.data.startswith("months:"):
        months = int(call.data.split(":")[1])
        selected[chat_id]['months'] = months
        bot.send_message(chat_id, "Введите сумму, которую вы хотите ПОЛУЧИТЬ (на руки):")

@bot.message_handler(func=lambda message: message.chat.id in selected and selected[message.chat.id]['months'] and not selected[message.chat.id]['amount'])
def get_amount(message):
    try:
        amount = float(message.text.replace(',', '.'))
    except:
        bot.send_message(message.chat.id, "Ошибка: введите число")
        return

    chat_id = message.chat.id
    selected[chat_id]['amount'] = amount

    bank = selected[chat_id]['bank']
    months = selected[chat_id]['months']
    amount = selected[chat_id]['amount']
    base_rate = TARIFFS[bank][months]
    extra = EXTRA_PRIVAT if bank == 'privat' else 0
    total_rate = base_rate + extra

    client_pays = amount / (1 - total_rate)
    per_month = client_pays / (months + 1)
    overpay = client_pays - amount

    text = f"📊 Расчёт по {bank.capitalize()}\n\n"
    text += f"Срок: {months} мес. ({months+1} платежей)\n"
    text += f"Сумма к получению: {amount:.2f} грн\n"
    if bank == 'privat':
        text += f"Ставка: {base_rate*100:.1f}% + {extra*100:.1f}% (эквайринг) = {total_rate*100:.1f}%\n"
    else:
        text += f"Ставка: {total_rate*100:.1f}%\n"
    text += f"Клиент заплатит: {client_pays:.2f} грн\n"
    text += f"Ежемесячно: {per_month:.2f} грн\n"
    text += f"Переплата: {overpay:.2f} грн\n\n"

    text += f"📈 Тарифы {bank.capitalize()}:\n"
    for m, rate in TARIFFS[bank].items():
        if bank == 'privat':
            text += f"{m} мес.: {rate*100:.1f}% + {EXTRA_PRIVAT*100:.1f}% = {(rate+EXTRA_PRIVAT)*100:.1f}%\n"
        else:
            text += f"{m} мес.: {rate*100:.1f}%\n"

    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("🔁 Сменить банк", callback_data="change:bank"),
        types.InlineKeyboardButton("💰 Изменить сумму", callback_data="change:amount")
    )
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("change:"))
def change_handler(call):
    chat_id = call.message.chat.id
    what = call.data.split(":")[1]
    if what == "bank":
        selected[chat_id] = {'bank': None, 'months': None, 'amount': None}
        start(call.message)
    elif what == "amount":
        selected[chat_id]['amount'] = None
        bot.send_message(chat_id, "Введите сумму, которую вы хотите ПОЛУЧИТЬ (на руки):")

bot.infinity_polling()
