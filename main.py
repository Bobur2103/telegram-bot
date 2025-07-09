import os
import json
import random
from flask import Flask
from threading import Thread
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from dotenv import load_dotenv

load_dotenv()

app = Flask('')

@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Telegram token
TOKEN = os.getenv("TELEGRAM_TOKEN")
REQUIRED_CHANNELS = os.getenv("CHANNELS").split(",")
bot = telebot.TeleBot(TOKEN)

LANG_PATH = 'langs'
USERS_FILE = 'users.json'

jokes = ["haa krisa 😂", "qzu bosa oxirigacha ko'r 😆", "voy dodaa 😅", "hech narsani o'tkazib yuborma 🤣"]

def load_language(lang_code):
    with open(f"{LANG_PATH}/{lang_code}.json", "r", encoding="utf-8") as f:
        return json.load(f)

def get_user_lang(user_id):
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    else:
        users = {}
    return users.get(str(user_id), "uz")

def set_user_lang(user_id, lang_code):
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
    else:
        users = {}
    users[str(user_id)] = lang_code
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def main_keyboard(lang):
    l = load_language(lang)
    kb = InlineKeyboardMarkup()
    kb.row(
        InlineKeyboardButton(l['start'], callback_data='start'),
        InlineKeyboardButton(l['language'], callback_data='language')
    )
    kb.row(
        InlineKeyboardButton(l['help'], callback_data='help'),
        InlineKeyboardButton(l['admin'], callback_data='admin')
    )
    kb.add(InlineKeyboardButton(l['code'], callback_data='code'))
    return kb

def check_subscription(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            chat_member = bot.get_chat_member(channel.strip(), user_id)
            if chat_member.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

def send_subscription_prompt(chat_id, lang):
    l = load_language(lang)
    text = l['subscribe_first']
    markup = InlineKeyboardMarkup()
    for ch in REQUIRED_CHANNELS:
        try:
            chat = bot.get_chat(ch.strip())
            if chat.username:
                markup.add(InlineKeyboardButton(l['subscribe_button'], url=f"https://t.me/{chat.username}"))
        except:
            continue
    bot.send_message(chat_id, text, reply_markup=markup)

@bot.message_handler(commands=['start'])
def send_start(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    bot.send_message(message.chat.id, l['welcome'], reply_markup=main_keyboard(lang))

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    lang = get_user_lang(call.from_user.id)
    l = load_language(lang)

    if call.data == 'start':
        bot.send_message(call.message.chat.id, l['welcome'], reply_markup=main_keyboard(lang))
    elif call.data == 'language':
        kb = InlineKeyboardMarkup()
        kb.row(
            InlineKeyboardButton("🇺🇿 Uzbek", callback_data='lang_uz'),
            InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru'),
            InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')
        )
        bot.send_message(call.message.chat.id, l['choose_language'], reply_markup=kb)
    elif call.data.startswith('lang_'):
        lang_code = call.data.split('_')[1]
        set_user_lang(call.from_user.id, lang_code)
        bot.send_message(call.message.chat.id, "✅ Til o'zgartirildi!", reply_markup=main_keyboard(lang_code))
    elif call.data == 'help':
        bot.send_message(call.message.chat.id, l['help_text'])
    elif call.data == 'admin':
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✉️ Admin bilan bogʻlanish", url="https://t.me/user6597938319"))
        bot.send_message(call.message.chat.id, l['admin_contact'], reply_markup=markup)
    elif call.data == 'code':
        bot.send_message(call.message.chat.id, l['enter_code'])

@bot.message_handler(func=lambda m: True)
def handle_code(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)

    if not check_subscription(message.from_user.id):
        send_subscription_prompt(message.chat.id, lang)
        return

    code = message.text.strip()
    filepath = f"static/videos/{code}.mp4"
    if os.path.exists(filepath):
        bot.send_chat_action(message.chat.id, "upload_video")
        with open(filepath, "rb") as video:
            bot.send_video(message.chat.id, video)
        bot.send_message(message.chat.id, random.choice(jokes))
    else:
        bot.send_message(message.chat.id, l['video_not_found'])

# Start bot
keep_alive()
bot.polling()
