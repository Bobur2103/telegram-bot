import os
import json
import requests
from flask import Flask
from threading import Thread
from dotenv import load_dotenv
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand

# --- CONFIGURATION ---
load_dotenv()
app = Flask('')
TOKEN = os.getenv("TELEGRAM_TOKEN")
REQUIRED_CHANNELS = os.getenv("CHANNELS", "").split(",")
ADMIN_ID = 6597938319
USERS_FILE = 'users.json'
CODES_FILE = 'codes.json'
STATS_FILE = 'stats.json'
LANG_PATH = 'langs'
FEEDBACK_STATE = {}
LAST_BOT_MESSAGES = {}

bot = telebot.TeleBot(TOKEN, parse_mode='HTML')

# --- KEEP ALIVE ---
@app.route('/')
def home():
    return "Bot is running!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    Thread(target=run).start()

# --- COMMANDS ---
bot.set_my_commands([
    BotCommand("start", "Bot haqida umumiy ma’lumot"),
    BotCommand("kod", "Kod orqali video izlash"),
    BotCommand("yordam", "Foydalanish bo’yicha yordam"),
    BotCommand("til", "Tilni o‘zgartirish"),
    BotCommand("shikoyat", "Admin bilan bog‘lanish"),
    BotCommand("maxfiylik", "Maxfiylik siyosati haqida"),
    BotCommand("fikr", "Fikr yuborish"),
    BotCommand("new", "Oxirgi qo‘shilgan videolar")
])

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
    users = {}
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            users = json.load(f)
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

# --- GOFILE LINK ---
def get_direct_gofile_link(gofile_url):
    try:
        file_id = gofile_url.strip().split("/")[-1]
        res = requests.get(f"https://api.gofile.io/getContent?contentId={file_id}&cache=true")
        file_data = list(res.json()["data"]["contents"].values())[0]
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
    markup = InlineKeyboardMarkup()
    for ch in REQUIRED_CHANNELS:
        markup.add(InlineKeyboardButton(f"@{ch}", url=f"https://t.me/{ch}"))
    send_or_edit(chat_id, l['subscribe_first'], markup)

# --- BOT MESSAGES ---
def send_or_edit(chat_id, text, reply_markup=None):
    msg_id = LAST_BOT_MESSAGES.get(chat_id)
    try:
        if msg_id:
            bot.edit_message_text(chat_id=chat_id, message_id=msg_id, text=text, reply_markup=reply_markup)
        else:
            msg = bot.send_message(chat_id, text, reply_markup=reply_markup)
            LAST_BOT_MESSAGES[chat_id] = msg.message_id
    except:
        msg = bot.send_message(chat_id, text, reply_markup=reply_markup)
        LAST_BOT_MESSAGES[chat_id] = msg.message_id

# --- COMMAND HANDLERS ---
@bot.message_handler(commands=['start'])
def start_cmd(message):
    uid = str(message.from_user.id)
    if not os.path.exists(USERS_FILE) or uid not in json.load(open(USERS_FILE)):
        set_user_lang(uid, "uz")
    lang = get_user_lang(uid)
    l = load_language(lang)
    send_or_edit(message.chat.id, l['welcome'])

@bot.message_handler(commands=['kod'])
def kod_cmd(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    send_or_edit(message.chat.id, l['enter_code'])

@bot.message_handler(commands=['yordam'])
def help_cmd(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    send_or_edit(message.chat.id, l['help_text'])

@bot.message_handler(commands=['til'])
def til_cmd(message):
    kb = InlineKeyboardMarkup()
    kb.row(InlineKeyboardButton("🇺🇿 Uzbek", callback_data='lang_uz'),
           InlineKeyboardButton("🇷🇺 Русский", callback_data='lang_ru'),
           InlineKeyboardButton("🇬🇧 English", callback_data='lang_en'))
    send_or_edit(message.chat.id, "Tilni tanlang / Select language", kb)

@bot.message_handler(commands=['maxfiylik'])
def privacy_cmd(message):
    text = (
        "<b>🔒 Maxfiylik siyosati</b>\n"
        "Ushbu Maxfiylik siyosati Telegram botimizdan foydalanganda ma'lumotlaringizni qanday to'plashimiz, ishlatishimiz, oshkor qilishimiz va himoya qilishimizni tushuntiradi. Agar bu siyosatga rozisiz, foydalanishni davom eting.\n\n"
        "<b>To'plangan ma'lumotlar:</b>\n- Telegram ID\n- Tanlangan til\n\n"
        "<b>Cookie va Kuzatuv:</b>\n- Cookie ishlatilmaydi.\n\n"
        "<b>Ijtimoiy tarmoqlardan:</b>\n- Faqat ochiq ma'lumotlardan foydalaniladi.\n\n"
        "<b>Xavfsizlik:</b>\n- Suhbatlar saqlanmaydi.\n- Jo'natilgan linklar xavfsiz."
    )
    send_or_edit(message.chat.id, text)

@bot.message_handler(commands=['fikr', 'shikoyat'])
def feedback_cmd(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    FEEDBACK_STATE[message.from_user.id] = True
    send_or_edit(message.chat.id, l['send_feedback'])

@bot.message_handler(commands=['new'])
def new_videos(message):
    if not os.path.exists(CODES_FILE): return
    with open(CODES_FILE, "r") as f:
        codes = list(json.load(f).keys())[-5:]
    send_or_edit(message.chat.id, "Oxirgi videolar: " + ", ".join(codes))

# --- FEEDBACK AND VIDEO CODE HANDLER ---
@bot.message_handler(func=lambda m: True)
def all_text_handler(message):
    uid = message.from_user.id
    lang = get_user_lang(uid)
    l = load_language(lang)

    if FEEDBACK_STATE.get(uid):
        text = f"✉️ Yangi fikr/shikoyat\nID: {uid}\nUsername: @{message.from_user.username or 'yo'q'}\nMatn: {message.text}"
        bot.send_message(ADMIN_ID, text)
        send_or_edit(message.chat.id, "✅ Rahmat! Xabaringiz yuborildi.")
        FEEDBACK_STATE[uid] = False
        return

    if not check_subscription(uid):
        send_subscription_prompt(message.chat.id, lang)
        return

    code = message.text.strip()
    if os.path.exists(f"static/videos/{code}.mp4"):
        with open(f"static/videos/{code}.mp4", "rb") as vid:
            bot.send_chat_action(message.chat.id, "upload_video")
            bot.send_video(message.chat.id, vid)
        update_video_stats(code)
        return

    if os.path.exists(CODES_FILE):
        with open(CODES_FILE, "r") as f:
            codes = json.load(f)
        if code in codes:
            link = get_direct_gofile_link(codes[code])
            if link:
                send_or_edit(message.chat.id, f"📽 <a href='{link}'>Videoni shu silkada joylashgan. Bemalol o'tib ko'rishingiz mumkin ☺</a>")
                update_video_stats(code)
                return
    send_or_edit(message.chat.id, l['video_not_found'])

# --- RUN BOT ---
keep_alive()
bot.polling()
