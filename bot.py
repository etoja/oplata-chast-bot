import telebot
from telebot import types
from tariffs import tariffs
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)
user_data = {}

@bot.message_handler(commands=['start', 'help'])
def start(message):
    user_data[message.chat.id] = {}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(*tariffs.keys())
    bot.send_message(message.chat.id, (
        "👋 <b>Я бот для расчёта переплаты при оплате частями.</b>\n\n"
        "🧾 <b>Как использовать:</b>\n"
        "1️⃣ Выбери банк\n"
        "2️⃣ Укажи срок (в месяцах)\n"
        "3️⃣ Введи сумму, которую хочешь получить\n"
        "— Я посчитаю сумму переплаты, ежемесячный платёж и дам тарифную таблицу.\n\n"
        "📲 После расчёта ты сможешь изменить параметры или перейти в бота для оформления.",
    ), parse_mode="HTML", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text in tariffs)
def choose_bank(message):
    user_data[message.chat.id] = {"bank": message.text}
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    options = [str(k) for k in tariffs[message.text].keys()]
    markup.add(*options)
    bot.send_message(message.chat.id, "📅 Выбери количество месяцев (не платежей!):", reply_markup=markup)

@bot.message_handler(func=lambda msg: msg.text.isdigit())
def choose_month_or_amount(message):
    chat_id = message.chat.id
    text = message.text
    data = user_data.get(chat_id, {})

    if "bank" in data and "months" not in data:
        months = int(text)
        if months in tariffs[data["bank"]]:
            user_data[chat_id]["months"] = months
            bot.send_message(chat_id, "💵 Введи сумму, которую ты хочешь получить:")
        else:
            bot.send_message(chat_id, "❌ Неправильное значение. Попробуй снова.")
    elif "months" in data:
        amount = float(text)
        bank = data["bank"]
        months = data["months"]
        rate = tariffs[bank][months]

        total = amount * (1 + rate)
        monthly = total / (months + 1)
        overpay = total - amount

        rate_table = "\n".join([f"{m} мес. — {int(r * 1000) / 10:.1f}%" for m, r in sorted(tariffs[bank].items())])

        text = (
            f"📊 <b>Расчёт по {bank}</b>\n"
            f"— <b>Срок:</b> {months} мес. ({months + 1} платежей)\n"
            f"— <b>Сумма к получению:</b> {amount:.2f} грн\n"
            f"— <b>Ставка:</b> {rate * 100:.1f}%\n"
            f"— <b>Клиент заплатит:</b> {total:.2f} грн\n"
            f"— <b>Ежемесячно:</b> {monthly:.2f} грн\n"
            f"— <b>Переплата:</b> {overpay:.2f} грн\n\n"
            f"📈 <b>Тарифы {bank}:</b>\n{rate_table}"
        )

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add("🔁 Изменить банк", "📅 Изменить срок")
        markup.add("💵 Изменить сумму", "🆕 Начать сначала")
        markup.add("🤝 Перейти к @chast_monobankbot", "🔙 Назад")

        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)

        # Автосброс после расчета
        user_data[chat_id] = {"bank": bank, "months": months, "amount": amount}

@bot.message_handler(func=lambda msg: msg.text in [
    "🔁 Изменить банк", "📅 Изменить срок", "💵 Изменить сумму", "🆕 Начать сначала",
    "🤝 Перейти к @chast_monobankbot", "🔙 Назад"
])
def handle_actions(message):
    chat_id = message.chat.id
    action = message.text

    if action == "🔁 Изменить банк" or action == "🆕 Начать сначала":
        user_data[chat_id] = {}
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(*tariffs.keys())
        bot.send_message(chat_id, "Выбери банк:", reply_markup=markup)

    elif action == "📅 Изменить срок":
        bank = user_data[chat_id].get("bank")
        if not bank:
            bot.send_message(chat_id, "Сначала выбери банк.")
            return
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        options = [str(k) for k in tariffs[bank].keys()]
        markup.add(*options)
        bot.send_message(chat_id, "Выбери количество месяцев:", reply_markup=markup)

    elif action == "💵 Изменить сумму":
        bot.send_message(chat_id, "Введи новую сумму:")

    elif action == "🤝 Перейти к @chast_monobankbot":
        summary = user_data.get(chat_id, {})
        msg = f"Хочу оформить рассрочку в Monobank. Сумма: {summary.get('amount', '—')} грн. Срок: {summary.get('months', '—')} мес."
        bot.send_message(chat_id, f"Перейди по ссылке 👉 <b>https://t.me/chast_monobankbot</b>\n\nСкопируй это сообщение:\n<code>{msg}</code>", parse_mode="HTML")

    elif action == "🔙 Назад":
        bot.send_message(chat_id, "Что хочешь изменить?", reply_markup=types.ReplyKeyboardRemove())
        start(message)

bot.polling()