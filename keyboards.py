from telebot.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton

def get_result_keyboard():
    kb = ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔁 Изменить банк", "📅 Изменить срок")
    kb.add("💵 Изменить сумму", "🆕 Начать сначала")
    return kb

def get_bank_link_keyboard(bank_name):
    links = {
        "Monobank": "https://t.me/chast_monobankbot",
        "ПУМБ": "https://t.me/smart_oplata_pumb_bot"
    }
    url = links.get(bank_name)
    if not url:
        return None
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(text=f"👉 Перейти в бот {bank_name}", url=url))
    return kb
