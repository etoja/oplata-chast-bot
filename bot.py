import telebot
from flask import Flask, request
import os

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")  # Убедись, что переменная окружения установлена
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Тарифы банков
bank_rates = {
    "mono": {
        2: 1.9,
        3: 2.9,
        4: 3.9,
        5: 4.9,
        6: 5.9,
    },
    "pumb": {
        2: 2.5,
        3: 3.7,
        4: 4.9,
        5: 6.1,
        6: 7.3,
    },
    "privat": {
        2: 1.7,
        3: 2.8,
        4: 4.5,
        5: 5.7,
        6: 6.9,
        7: 8.0,
    }
}

bank_names = {
    "mono": "МоноБанк",
    "pumb": "ПУМБ",
    "privat": "ПриватБанк"
}

# Вебхук
@app.route('/', methods=['POST'])
def webhook():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    else:
        return 'Invalid request', 403

# Команда старт
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.send_message(message.chat.id,
                     "👋 Привет! Введи данные в формате:\n\n<банк> <срок в месяцах> <сумма>\n\n"
                     "Например:\nmono 3 1000\n\n"
                     "Доступные банки: mono, pumb, privat")

# Основная логика
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    try:
        parts = message.text.lower().split()
        if len(parts) != 3:
            bot.reply_to(message, "❌ Неверный формат. Используй: <банк> <срок> <сумма>")
            return

        bank_key, months_str, amount_str = parts
        months = int(months_str)
        desired_amount = float(amount_str)

        if bank_key not in bank_rates:
            bot.reply_to(message, "❌ Неизвестный банк. Используй: mono, pumb, privat")
            return

        rates = bank_rates[bank_key]
        if months not in rates:
            bot.reply_to(message, f"❌ Недоступный срок для {bank_names[bank_key]}")
            return

        base_rate = rates[months]

        # Добавляем 1.3% для ПриватБанка (эквайринг)
        if bank_key == "privat":
            acquiring_fee = 1.3
            total_rate = base_rate + acquiring_fee
            breakdown = f"{base_rate:.1f}% + {acquiring_fee:.1f}% (эквайринг) = {total_rate:.1f}%"
        else:
            total_rate = base_rate
            breakdown = f"{total_rate:.1f}%"

        # Расчёт итоговой суммы, чтобы получить на руки desired_amount
        client_pays = desired_amount / (1 - total_rate / 100)
        monthly = client_pays / (months + 1)
        overpay = client_pays - desired_amount

        result = (
            f"📊 Расчёт по {bank_names[bank_key]}\n\n"
            f"Срок: {months} мес. ({months + 1} платежей)\n"
            f"Сумма к получению: {desired_amount:.2f} грн\n"
            f"Ставка: {breakdown}\n"
            f"Клиент заплатит: {client_pays:.2f} грн\n"
            f"Ежемесячно: {monthly:.2f} грн\n"
            f"Переплата: {overpay:.2f} грн\n\n"
            f"📈 Тарифы {bank_names[bank_key]}:\n" +
            "\n".join([f"{m} мес.: {round(r + (1.3 if bank_key == 'privat' else 0), 1)}%" for m, r in rates.items()])
        )

        bot.send_message(message.chat.id, result)
    except Exception as e:
        print(f"Ошибка: {e}")
        bot.reply_to(message, "❌ Произошла ошибка при обработке. Убедись в правильности данных.")

# Установи webhook вручную, если ещё не установил
# bot.set_webhook(url='https://oplata-chast-bot.onrender.com')

# Запускай через Flask
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
