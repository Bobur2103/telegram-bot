import os
import json
import requests
from flask import Flask, request
from dotenv import load_dotenv
import telebot
from telebot.types import BotCommand, InlineKeyboardMarkup, InlineKeyboardButton

# Load .env
load_dotenv()

# Flask app
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot ishlayapti!"

# --- CONFIGURATION ---
TOKEN = os.getenv("TELEGRAM_TOKEN")
REQUIRED_CHANNELS = os.getenv("CHANNELS", "").split(",")  # channel IDs like -1001234567890
ADMIN_ID = 6597938319
bot = telebot.TeleBot(TOKEN)

LANG_PATH = 'langs'
USERS_FILE = 'users.json'
CODES_FILE = 'codes.json'
STATS_FILE = 'stats.json'
FEEDBACK_STATE = {}
LAST_MESSAGES = {}

# --- FUNCTIONS ---
def load_language(code):
    path = f"{LANG_PATH}/{code}.json"
    with open(path, "r", encoding="utf-8") as f:
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
    return gofile_url.strip()

def check_subscription(user_id):
    for ch_id in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(ch_id, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

def send_subscription_prompt(chat_id, lang):
    l = load_language(lang)
    markup = InlineKeyboardMarkup()
    for ch_id in REQUIRED_CHANNELS:
        try:
            chat = bot.get_chat(ch_id)
            title = chat.title
            invite_link = f"https://t.me/{chat.username}" if chat.username else chat.invite_link
            if not invite_link:
                invite_link = f"https://t.me/c/{str(ch_id)[4:]}"
            markup.add(InlineKeyboardButton(text=title, url=invite_link))
        except:
            continue
    bot.send_message(chat_id, l['subscribe_first'], reply_markup=markup)

def send_or_edit_message(user_id, text, **kwargs):
    if LAST_MESSAGES.get(user_id):
        try:
            bot.delete_message(user_id, LAST_MESSAGES[user_id])
        except:
            pass
    msg = bot.send_message(user_id, text, **kwargs)
    LAST_MESSAGES[user_id] = msg.message_id

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.from_user.id
    if not os.path.exists(USERS_FILE) or str(user_id) not in json.load(open(USERS_FILE)):
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

    markup = InlineKeyboardMarkup()
    markup.row(
        InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="lang_uz"),
        InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru"),
        InlineKeyboardButton("🇺🇸 English", callback_data="lang_en")
    )
    send_or_edit_message(message.chat.id, l['choose_language'], reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("lang_"))
def handle_lang_callback(call):
    code = call.data.split("_")[1]
    set_user_lang(call.from_user.id, code)
    l = load_language(code)
    try:
        bot.edit_message_text(
            f"✅ Til o'zgartirildi!\n\n{l['welcome']}",
            chat_id=call.message.chat.id,
            message_id=call.message.message_id
        )
    except:
        bot.send_message(call.message.chat.id, f"✅ Til o'zgartirildi!\n\n{l['welcome']}")

@bot.message_handler(commands=['shikoyat', 'fikr'])
def handle_feedback(message):
    FEEDBACK_STATE[message.from_user.id] = True
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    send_or_edit_message(message.chat.id, l['send_feedback'])

@bot.message_handler(commands=['maxfiylik'])
def handle_privacy(message):
    lang = get_user_lang(message.from_user.id)
    l = load_language(lang)
    send_or_edit_message(message.chat.id, l['privacy'])

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
        send_or_edit_message(message.chat.id, l['feedback_thanks'])
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
        return

    if os.path.exists(CODES_FILE):
        with open(CODES_FILE) as f:
            codes = json.load(f)
        if code in codes:
            gofile_url = codes[code]
            direct_link = get_direct_gofile_link(gofile_url)
            if direct_link:
                bot.send_message(message.chat.id, f"Video shu silkada joylashgan. Bemalol o'tib ko'rishingiz mumkin ☺\n{direct_link}")
                update_video_stats(code)
                return

    send_or_edit_message(message.chat.id, l['video_not_found'])

# --- Webhook endpoint ---
@app.route(f'/{TOKEN}', methods=['POST'])
def receive_update():
    update = telebot.types.Update.de_json(request.stream.read().decode("utf-8"))
    bot.process_new_updates([update])
    return "OK", 200

# --- Start server and set webhook ---
if __name__ == "__main__":
    WEBHOOK_URL = f"https://telegram-bot-e33n.onrender.com/{TOKEN}"
    bot.remove_webhook()
    bot.set_webhook(url=WEBHOOK_URL)
    app.run(host="0.0.0.0", port=8080)
