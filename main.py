import os
import json
import requests
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton

# --- LOAD ENV ---
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")
REQUIRED_CHANNELS = os.getenv("CHANNELS").split(",")
ADMIN_ID = 6597938319

# --- INIT ---
bot = telebot.TeleBot(TOKEN)
app = Flask('')
LANG_PATH = 'langs'
USERS_FILE = 'users.json'
CODES_FILE = 'codes.json'
STATS_FILE = 'stats.json'
FEEDBACK_STATE = {}
LAST_BOT_MESSAGES = {}

# --- FLASK KEEP ALIVE ---
@app.route('/')
def home():
    return "I'm alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- LANGUAGE ---
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

# --- STATS ---
def update_video_stats(code):
    stats = {}
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, "r") as f:
            stats = json.load(f)
    stats[code] = stats.get(code, 0) + 1
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f)

# --- GOFILE ---
def get_direct_gofile_link(gofile_url):
    file_id = gofile_url.strip().split("/")[-1]
    try:
        response = requests.get(f"https://api.gofile.io/getContent?contentId={file_id}&token=&websiteToken=websiteToken&cache=true")
        data = response.json()
        file_data = list(data["data"]["contents"].values())[0]
        return file_data["link"]
    except:
        return None

# --- SUBSCRIPTION ---
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
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    for ch in REQUIRED_CHANNELS:
        try:
            chat = bot.get_chat(ch.strip())
            if chat.username:
                markup.add(KeyboardButton(f"https://t.me/{chat.username}"))
        except:
            continue
    send_new(chat_id, l['subscribe_first'], markup)

# --- MAIN MENU ---
def main_menu():
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.add(KeyboardButton("/start \u2022 Bot haqida umumiy ma'lumot"))
    menu.add(KeyboardButton("/kod \u2022 Kod orqali video izlash"))
    menu.add(KeyboardButton("/yordam \u2022 Foydalanish bo'yicha yordam"))
    menu.add(KeyboardButton("/til \u2022 Tilni o'zgartirish"))
    menu.add(KeyboardButton("/fikr \u2022 Fikr yuborish"))
    menu.add(KeyboardButton("/shikoyat \u2022 Shikoyat yuborish"))
    menu.add(KeyboardButton("/maxfiylik \u2022 Maxfiylik siyosati"))
    menu.add(KeyboardButton("/new \u2022 Oxirgi qo'shilgan videolar"))
    return menu

# --- BOT SEND WITH DELETE ---
def send_new(chat_id, text, reply_markup=None):
    old_msg = LAST_BOT_MESSAGES.get(chat_id)
    if old_msg:
        try:
            bot.delete_message(chat_id, old_msg)
        except:
            pass
    new_msg = bot.send_message(chat_id, text, reply_markup=reply_markup)
    LAST_BOT_MESSAGES[chat_id] = new_msg.message_id

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = str(message.from_user.id)
    if not os.path.exists(USERS_FILE) or user_id not in json.load(open(USERS_FILE)):
        set_user_lang(user_id, "uz")
    lang = get_user_lang(user_id)
    l = load_language(lang)
    send_new(message.chat.id, l['welcome'], main_menu())

@bot.message_handler(commands=['yordam'])
def handle_help(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    send_new(message.chat.id, l['help_text'], main_menu())

@bot.message_handler(commands=['til'])
def handle_language(message):
    lang_msg = "Tilni tanlang / Choose language"
    menu = ReplyKeyboardMarkup(resize_keyboard=True)
    menu.row(KeyboardButton("/lang_uz 🇺🇿"), KeyboardButton("/lang_ru 🇷🇺"), KeyboardButton("/lang_en 🇬🇧"))
    send_new(message.chat.id, lang_msg, menu)

@bot.message_handler(commands=['lang_uz', 'lang_ru', 'lang_en'])
def change_lang(message):
    lang_code = message.text.split('_')[1]
    set_user_lang(message.from_user.id, lang_code)
    send_new(message.chat.id, "✅ Til o'zgartirildi!", main_menu())

@bot.message_handler(commands=['shikoyat', 'fikr'])
def handle_feedback(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    FEEDBACK_STATE[message.from_user.id] = True
    send_new(message.chat.id, l['send_feedback'], main_menu())

@bot.message_handler(commands=['maxfiylik'])
def handle_privacy(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    send_new(message.chat.id, l['privacy_policy'], main_menu())

@bot.message_handler(commands=['new'])
def handle_new(message):
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE, "r") as f:
            codes = json.load(f)
        keys = list(codes.keys())[-5:]
        msg = '\n'.join(keys)
        send_new(message.chat.id, "🆕 Oxirgi kodlar:\n" + msg, main_menu())

@bot.message_handler(commands=['kod'])
def handle_code_prompt(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    send_new(message.chat.id, l['enter_code'], main_menu())

@bot.message_handler(func=lambda m: True)
def handle_messages(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    l = load_language(lang)

    if FEEDBACK_STATE.get(user_id):
        msg = f"✉️ Fikr yoki shikoyat:\nID: {user_id}\nUsername: @{message.from_user.username}\nXabar: {message.text}"
        bot.send_message(ADMIN_ID, msg)
        bot.send_message(message.chat.id, "✅ Rahmat! Xabaringiz yuborildi.")
        FEEDBACK_STATE[user_id] = False
        return

    if not check_subscription(user_id):
        send_subscription_prompt(message.chat.id, lang)
        return

    code = message.text.strip()
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE, "r") as f:
            codes = json.load(f)
        if code in codes:
            link = get_direct_gofile_link(codes[code])
            if link:
                update_video_stats(code)
                send_new(message.chat.id, l['video_link_msg'] + f"\n{link}", main_menu())
            else:
                send_new(message.chat.id, l['video_not_found'], main_menu())
        else:
            send_new(message.chat.id, l['video_not_found'], main_menu())
    else:
        send_new(message.chat.id, l['video_not_found'], main_menu())

# --- RUN ---
keep_alive()
bot.polling()
