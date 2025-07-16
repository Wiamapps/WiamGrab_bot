# smart_reply.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from faq_data import FAQ_DATA  # ✅ Now it's coming from its own file

def get_faq_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    for question in FAQ_DATA.keys():
        keyboard.add(InlineKeyboardButton(question, callback_data=f"faq:{question}"))
    return keyboard

def get_related_keyboard(question):
    keyboard = InlineKeyboardMarkup(row_width=2)
    related = FAQ_DATA[question].get("related", [])
    for rel in related:
        keyboard.add(InlineKeyboardButton(rel, callback_data=f"faq:{rel}"))
    return keyboard
