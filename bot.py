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
        base_rate = tariffs[bank][months]
        extra_rate = 0

        # Если банк Приват — добавляем +1.3%
        if bank.lower() in ["приват", "privatbank", "приватбанк"]:
            extra_rate = 0.013

        total_rate = base_rate + extra_rate
        total = amount / (1 - total_rate)
        monthly = total / (months + 1)
        overpay = total - amount

        user_data[chat_id]["amount"] = amount

        # Создание таблицы ставок без учёта надбавки
        rate_table = "\n".join([
            f"<b>{m} мес.</b>: {int(r * 1000)/10:.1f}%"
            for m, r in sorted(tariffs[bank].items())
        ])

        # Формирование строки с процентной ставкой
        if extra_rate > 0:
            rate_str = f"{base_rate * 100:.1f}% + {extra_rate * 100:.1f}% = {total_rate * 100:.1f}%"
        else:
            rate_str = f"{total_rate * 100:.1f}%"

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
