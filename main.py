import os
import json
import requests
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
import telebot
from telebot.types import BotCommand

# Load environment variables
load_dotenv()

app = Flask(__name__)

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
REQUIRED_CHANNELS = os.getenv("CHANNELS", "").split(",")
ADMIN_ID = 6597938319
bot = telebot.TeleBot(TOKEN)

LANG_PATH = 'langs'
USERS_FILE = 'users.json'
CODES_FILE = 'codes.json'
STATS_FILE = 'stats.json'
FEEDBACK_STATE = {}
LAST_MESSAGES = {}

# --- HELPER FUNCTIONS ---
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
    try:
        file_id = gofile_url.strip().split("/")[-1]
        response = requests.get(f"https://api.gofile.io/getContent?contentId={file_id}&cache=true")
        data = response.json()
        if data.get("status") != "ok":
            return None
        contents = data["data"].get("contents", {})
        if not contents:
            return None
        first_file = list(contents.values())[0]
        return first_file.get("link")
    except Exception as e:
        print("GOFILE ERROR:", e)
        return None

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
    text = l['subscribe_first'] + "\n\n" + "\n".join([f"\u27a1\ufe0f @{bot.get_chat(ch.strip()).username}" for ch in REQUIRED_CHANNELS])
    bot.send_message(chat_id, text)

def send_or_edit_message(user_id, text, **kwargs):
    if LAST_MESSAGES.get(user_id):
        try:
            bot.delete_message(user_id, LAST_MESSAGES[user_id])
        except:
            pass
    msg = bot.send_message(user_id, text, **kwargs)
    LAST_MESSAGES[user_id] = msg.message_id

# --- BOT COMMANDS ---
COMMANDS = [
    BotCommand("start", "Bot haqida umumiy ma’lumot"),
    BotCommand("kod", "Kod orqali video izlash"),
    BotCommand("yordam", "Foydalanish bo’yicha yordam"),
    BotCommand("til", "Tilni o‘zgartirish"),
    BotCommand("shikoyat", "Shikoyat yuborish"),
    BotCommand("maxfiylik", "Maxfiylik siyosati haqida"),
    BotCommand("fikr", "Fikr bildirish"),
    BotCommand("new", "Oxirgi yuklangan videolar")
]
bot.set_my_commands(COMMANDS)

# --- MESSAGE HANDLERS ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = str(message.from_user.id)
    if not os.path.exists(USERS_FILE) or user_id not in json.load(open(USERS_FILE)):
        set_user_lang(user_id, "uz")
    lang = get_user_lang(user_id)
    l = load_language(lang)
    send_or_edit_message(message.chat.id, l['welcome'])

@bot.message_handler(commands=['yordam'])
def handle_help(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    send_or_edit_message(message.chat.id, l['help_text'])

@bot.message_handler(commands=['til'])
def handle_lang(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    msg = "\n".join([
        "/til uz - O'zbekcha",
        "/til ru - Русский",
        "/til en - English"
    ])
    send_or_edit_message(message.chat.id, l['choose_language'] + "\n" + msg)

@bot.message_handler(func=lambda m: m.text and m.text.startswith('/til '))
def set_lang(message):
    code = message.text.split()[-1]
    if code in ['uz', 'ru', 'en']:
        set_user_lang(message.from_user.id, code)
        l = load_language(code)
        send_or_edit_message(message.chat.id, "✅ Til o‘zgartirildi!\n" + l['welcome'])

@bot.message_handler(commands=['shikoyat', 'fikr'])
def start_feedback(message):
    FEEDBACK_STATE[message.from_user.id] = True
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    send_or_edit_message(message.chat.id, l['send_feedback'])

@bot.message_handler(commands=['maxfiylik'])
def handle_privacy(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    send_or_edit_message(message.chat.id, l['privacy'])

@bot.message_handler(commands=['new'])
def handle_new(message):
    if os.path.exists(CODES_FILE):
        with open(CODES_FILE) as f:
            codes = list(json.load(f).keys())[-5:]
            send_or_edit_message(message.chat.id, "Oxirgi videolar: \n" + "\n".join(codes))

@bot.message_handler(commands=['kod'])
def request_code(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    send_or_edit_message(message.chat.id, l['enter_code'])

@bot.message_handler(func=lambda m: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    lang = get_user_lang(user_id)
    l = load_language(lang)

    if FEEDBACK_STATE.get(user_id):
        username = message.from_user.username or "yo'q"
        text = f"✉️ Yangi fikr/shikoyat\nID: {user_id}\nUsername: @{username}\nMatn: {message.text}"
        bot.send_message(ADMIN_ID, text)
        send_or_edit_message(message.chat.id, "✅ Rahmat! Xabaringiz yuborildi.")
        FEEDBACK_STATE[user_id] = False
        return

    if not check_subscription(user_id):
        send_subscription_prompt(message.chat.id, lang)
        return

    code = message.text.strip()
    local_path = f"static/videos/{code}.mp4"
    if os.path.exists(local_path):
        with open(local_path, "rb") as vid:
            bot.send_video(message.chat.id, vid)
        update_video_stats(code)
    elif os.path.exists(CODES_FILE):
        with open(CODES_FILE) as f:
            codes = json.load(f)
        if code in codes:
            gofile_url = codes[code]
            direct_link = get_direct_gofile_link(gofile_url)
            if direct_link:
                bot.send_message(message.chat.id, f"Videoni shu silkada joylashgan. Bemalol o'tib ko'rishingiz mumkin ☺\n{direct_link}")
                update_video_stats(code)
            else:
                send_or_edit_message(message.chat.id, l['video_not_found'])
        else:
            send_or_edit_message(message.chat.id, l['video_not_found'])
    else:
        send_or_edit_message(message.chat.id, l['video_not_found'])

# --- START ---
keep_alive()
bot.polling()
