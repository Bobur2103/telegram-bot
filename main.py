import os
import json
import random
import requests
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Load environment
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

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
REQUIRED_CHANNELS = os.getenv("CHANNELS").split(",")
ADMIN_ID = 6597938319
bot = telebot.TeleBot(TOKEN)

LANG_PATH = 'langs'
USERS_FILE = 'users.json'
CODES_FILE = 'codes.json'
STATS_FILE = 'stats.json'
FEEDBACK_STATE = {}

jokes = ["haa krisa 😂", "qzu bosa oxirigacha ko'r 😆", "voy dodaa 😅", "hech narsani o'tkazib yuborma 🤣"]

# --- HELPERS ---
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

def update_video_stats(code):
    stats = {}
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            stats = json.load(f)
    stats[code] = stats.get(code, 0) + 1
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)

def get_direct_gofile_link(gofile_url):
    file_id = gofile_url.strip().split("/")[-1]
    try:
        response = requests.get(f"https://api.gofile.io/getContent?contentId={file_id}&token=&websiteToken=websiteToken&cache=true")
        data = response.json()
        file_data = list(data["data"]["contents"].values())[0]
        return file_data["link"]
    except:
        return None

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
        InlineKeyboardButton("📢 " + l['feedback'], callback_data='feedback')
    )
    kb.add(InlineKeyboardButton(l['code'], callback_data='code'))
    return kb

def check_subscription(user_id):
    for channel in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(channel.strip(), user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

def send_subscription_prompt(chat_id, lang):
    l = load_language(lang)
    markup = InlineKeyboardMarkup()
    for ch in REQUIRED_CHANNELS:
        try:
            chat = bot.get_chat(ch.strip())
            if chat.username:
                markup.add(InlineKeyboardButton(l['subscribe_button'], url=f"https://t.me/{chat.username}"))
        except:
            continue
    bot.send_message(chat_id, l['subscribe_first'], reply_markup=markup)

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = str(message.from_user.id)
    if not os.path.exists(USERS_FILE) or user_id not in json.load(open(USERS_FILE)):
        set_user_lang(user_id, "uz")  # Default
    lang = get_user_lang(user_id)
    l = load_language(lang)
    bot.send_message(message.chat.id, l['welcome'], reply_markup=main_keyboard(lang))

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    user_id = str(call.from_user.id)
    lang = get_user_lang(user_id)
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
        bot.send_message(call.message.chat.id, l['send_feedback'])
        FEEDBACK_STATE[call.from_user.id] = True

@bot.message_handler(commands=['stats'])
def handle_admin_stats(message):
    if message.from_user.id == ADMIN_ID:
        with open(USERS_FILE, "r") as f:
            user_count = len(json.load(f))
        with open(STATS_FILE, "r") as f:
            stats = json.load(f)
        total_requests = sum(stats.values())
        bot.send_message(message.chat.id, f"👥 Users: {user_count}\n🎞 Total requests: {total_requests}")

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.from_user.id == ADMIN_ID:
        text = message.text.replace('/broadcast', '').strip()
        if not text:
            return bot.reply_to(message, "Matn yuboring: /broadcast [matn]")
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
        for uid in users:
            try:
                bot.send_message(uid, text)
            except:
                continue
        bot.send_message(message.chat.id, "✅ Yuborildi.")

@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    l = load_language(lang)

    if FEEDBACK_STATE.get(user_id):
        bot.send_message(ADMIN_ID, f"✉️ Yangi fikr/shikoyat:\n\n👤 ID: {user_id}\n📨 {message.text}")
        bot.send_message(message.chat.id, "✅ Rahmat! Xabaringiz yuborildi.")
        FEEDBACK_STATE[user_id] = False
        return

    if not check_subscription(user_id):
        send_subscription_prompt(message.chat.id, lang)
        return

    code = message.text.strip()
    local_path = f"static/videos/{code}.mp4"
    if os.path.exists(local_path):
        bot.send_chat_action(message.chat.id, "upload_video")
        with open(local_path, "rb") as vid:
            bot.send_video(message.chat.id, vid)
        update_video_stats(code)
        bot.send_message(message.chat.id, random.choice(jokes))
    elif os.path.exists(CODES_FILE):
        with open(CODES_FILE, "r") as f:
            codes = json.load(f)
        if code in codes:
            gofile_url = codes[code]
            direct_link = get_direct_gofile_link(gofile_url)
            if direct_link:
                bot.send_chat_action(message.chat.id, "upload_video")
                bot.send_video(message.chat.id, direct_link)
                update_video_stats(code)
                bot.send_message(message.chat.id, random.choice(jokes))
            else:
                bot.send_message(message.chat.id, l['video_not_found'])
        else:
            bot.send_message(message.chat.id, l['video_not_found'])
    else:
        bot.send_message(message.chat.id, l['video_not_found'])

# --- RUN BOT ---
keep_alive()
bot.polling()
