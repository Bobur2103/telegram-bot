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

# Telegram token va kerakli kanallar
TOKEN = os.getenv("TELEGRAM_TOKEN")
REQUIRED_CHANNELS = os.getenv("CHANNELS").split(",")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = telebot.TeleBot(TOKEN)

LANG_PATH = 'langs'
USERS_FILE = 'users.json'
CODES_FILE = 'codes.json'
STATS_FILE = 'stats.json'

jokes = [
    "haa krisa 😂", "qzu bosa oxirigacha ko'r 😆",
    "voy dodaa degin 😅", "hech narsani o'tkazib yuborma 🤣"
]

# Tilni yuklash
def load_language(lang_code):
    with open(f"{LANG_PATH}/{lang_code}.json", "r", encoding="utf-8") as f:
        return json.load(f)

# Foydalanuvchi tili
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

# Statistikani yangilash
def update_stats(code):
    stats = {}
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            stats = json.load(f)
    stats[code] = stats.get(code, 0) + 1
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)

# Asosiy tugmalar
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
    kb.row(
        InlineKeyboardButton(l['code'], callback_data='code'),
        InlineKeyboardButton(l['feedback'], callback_data='feedback'),
        InlineKeyboardButton(l['stats'], callback_data='stats')
    )
    return kb

# Obuna tekshirish
def check_subscription(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            chat_member = bot.get_chat_member(channel.strip(), user_id)
            if chat_member.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

# Obuna so‘rovi
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
        markup.add(InlineKeyboardButton("✉️ Admin bilan bogʻlanish", url="https://t.me/pep_xi"))
        bot.send_message(call.message.chat.id, l['admin_contact'], reply_markup=markup)
    elif call.data == 'code':
        bot.send_message(call.message.chat.id, l['enter_code'])
    elif call.data == 'feedback':
        bot.send_message(call.message.chat.id, l['feedback_prompt'])
    elif call.data == 'stats':
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        stats = {}
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r") as f:
                stats = json.load(f)
        total_requests = sum(stats.values())
        bot.send_message(call.message.chat.id, f"👥 Foydalanuvchilar: {len(users)}\n🎞 Video so'rovlar: {total_requests}")

# Feedback xabarlari
@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)

    if not check_subscription(message.from_user.id):
        send_subscription_prompt(message.chat.id, lang)
        return

    if message.text:
        code = message.text.strip()

        # Kod orqali tekshir
        filepath = f"static/videos/{code}.mp4"
        if os.path.exists(filepath):
            bot.send_chat_action(message.chat.id, "upload_video")
            with open(filepath, "rb") as video:
                bot.send_video(message.chat.id, video)
            update_stats(code)
            bot.send_message(message.chat.id, random.choice(jokes))
            return

        # Havolali kod
        if os.path.exists(CODES_FILE):
            with open(CODES_FILE, "r") as f:
                codes = json.load(f)
            if code in codes:
                url = codes[code]
                bot.send_chat_action(message.chat.id, "upload_video")
                bot.send_video(message.chat.id, url)
                update_stats(code)
                bot.send_message(message.chat.id, random.choice(jokes))
                return

        # Agar kod emas, adminga yuboriladi (fikr/shikoyat sifatida)
        text = f"📩 Yangi fikr/shikoyat:\nFrom: {message.from_user.first_name} ({message.from_user.id})\n\n{text}"
        bot.send_message(ADMIN_ID, text)
        bot.send_message(message.chat.id, l['feedback_sent'])

# Boshlash
keep_alive()
bot.polling()
