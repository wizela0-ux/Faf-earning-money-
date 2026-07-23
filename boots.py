import telebot
from telebot import types
import requests
import json
from flask import Flask, request
import os
import threading

# ==================== 1. ያንተ መረጃዎች (እነዚህን ብቻ ቀይር) ====================
BOT_TOKEN = "8366647485:AAFZbHSaLgVGCBNw2PiS2LpEnphFv9MAeMU"          # የቦትህ ቶክን
CHANNEL_ID = "@YOUR_CHANNEL_USERNAME"      # የቻናልህ ማስተላለፊያ (e.g., @mychannel)
ADMIN_CHAT_ID = "YOUR_ADMIN_CHAT_ID"       # ያንተ የቴሌግራም ID
FIREBASE_URL = "https://faf-earning-money-default-rtdb.firebaseio.com/" # የፌርቤዝ ሊንክ
WEB_APP_URL = "https://faf-premium-app.vercel.app" # ቨርሰል ላይ የሰቀልከው አዲሱ ሊንክ

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

# ሰርቨሩ በቋሚነት እንዲነቃቃ የተሰራ ቀላል ገጽ
@app.route('/')
def home():
    return "FAF Bot is running 24/7!"

# ==================== 2. ቦቱ ሲነሳ (/start) ====================
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username if message.from_user.username else "User"
    
    user_ref = requests.get(f"{FIREBASE_URL}users/{user_id}.json").json()
    if not user_ref:
        new_user = {
            "username": username,
            "balance": 0.00,
            "ads_count": 0,
            "total_invites": 0,
            "join_date": "2026-07-24"
        }
        requests.patch(f"{FIREBASE_URL}users/{user_id}.json", json.dumps(new_user))

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    web_app_info = types.WebAppInfo(WEB_APP_URL)
    web_app_button = types.KeyboardButton(text="📱 Open FAF Hub", web_app=web_app_info)
    markup.add(web_app_button)

    welcome_text = (
        f"እንኳን ወደ FAF Earning Hub በሰላም መጡ፣ @{username}! 👋\n\n"
        "ከታች ያለውን <b>📱 Open FAF Hub</b> የሚለውን ቁልፍ በመንካት "
        "ማስታወቂያዎችን ማየት እና ታስኮችን መስራት መጀመር ይችላሉ።"
    )
    bot.send_message(message.chat.id, welcome_text, parse_mode="HTML", reply_markup=markup)

# ==================== 3. የክፍያ ጥያቄ መከታተያ ====================
@bot.message_handler(commands=['check_withdrawals'])
def check_withdrawals(message):
    if str(message.chat.id) != str(ADMIN_CHAT_ID):
        return

    try:
        requests_ref = requests.get(f"{FIREBASE_URL}withdraw_requests.json").json()
        if not requests_ref:
            bot.send_message(ADMIN_CHAT_ID, "📭 በአሁኑ ሰአት ምንም አዲስ የክፍያ ጥያቄ የለም።")
            return

        for req_id, req_data in requests_ref.items():
            user_id = req_data.get("user_id")
            amount = req_data.get("amount")
            method = req_data.get("method")
            account = req_data.get("account")
            uname = req_data.get("username", "ተጠቃሚ")

            admin_msg = (
                f"🚨 <b>አዲስ የክፍያ ጥያቄ መጥቷል!</b>\n\n"
                f"👤 ተጠቃሚ፦ @{uname} ({user_id})\n"
                f"💰 መጠን፦ {amount} ETB\n"
                f"💳 ዘዴ፦ {method.upper()}\n"
                f"📌 አካውንት ቁጥር፦ <code>{account}</code>\n"
            )
            
            markup = types.InlineKeyboardMarkup()
            approve_btn = types.InlineKeyboardButton("✅ ይከፈል (Approve)", callback_data=f"app_{req_id}_{user_id}_{amount}")
            reject_btn = types.InlineKeyboardButton("❌ ይሰረዝ (Reject)", callback_data=f"rej_{req_id}_{user_id}_{amount}")
            markup.add(approve_btn, reject_btn)
            
            bot.send_message(ADMIN_CHAT_ID, admin_msg, parse_mode="HTML", reply_markup=markup)

    except Exception as e:
        print(f"Error checking requests: {e}")

# ==================== 4. የአድሚኑ ምርጫ (Approve / Reject) ====================
@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    data_parts = call.data.split("_")
    action = data_parts[0]
    req_id = data_parts[1]
    target_user_id = data_parts[2]
    amount = data_parts[3]

    if action == "app":
        try:
            user_msg = f"🎉 እንኳን ደስ አለዎት! ያቀረቡት የ {amount} ETB የክፍያ ጥያቄ በአድሚኑ ጸድቆ በቴሌብር/ባንክ ተልኮልዎታል።"
            bot.send_message(target_user_id, user_msg)
        except:
            pass
        
        try:
            channel_msg = f"💰 <b>ስኬታማ ክፍያ!</b>\n\n👤 ተጠቃሚ፦ ID ***{target_user_id[-4:]}\n💵 መጠን፦ {amount} ETB\n⚡️ ሁኔታ፦ ተከፍሏል (Paid) ✅\n\nFAF Earning Hub ታማኝነቱ የተመሰከረለት ነው! 🚀"
            bot.send_message(CHANNEL_ID, channel_msg, parse_mode="HTML")
        except:
            pass

        requests.delete(f"{FIREBASE_URL}withdraw_requests/{req_id}.json")
        bot.edit_message_text("✅ ክፍያው ጸድቋል፤ ለተጠቃሚውና ለቻናሉ መረጃው ተልኳል።", chat_id=call.message.chat.id, message_id=call.message.message_id)

    elif action == "rej":
        user_data = requests.get(f"{FIREBASE_URL}users/{target_user_id}.json").json()
        if user_data:
            current_bal = float(user_data.get("balance", 0))
            requests.patch(f"{FIREBASE_URL}users/{target_user_id}.json", json.dumps({"balance": current_bal + float(amount)}))
        
        try:
            bot.send_message(target_user_id, f"⚠️ ያቀረቡት የ {amount} ETB የክፍያ ጥያቄ ውድቅ ተደርጓል፤ ብሩ ወደ ቦት አካውንትዎ ተመልሷል።")
        except:
            pass

        requests.delete(f"{FIREBASE_URL}withdraw_requests/{req_id}.json")
        bot.edit_message_text("❌ የክፍያ ጥያቄው ውድቅ ተደርጓል፤ ብሩ ተመልሷል።", chat_id=call.message.chat.id, message_id=call.message.message_id)

# ቦቱን ከበስተጀርባ ለማስነሳት
def run_bot():
    bot.infinity_polling()

if __name__ == "__main__":
    # ቦቱን በ Thread ማስነሳት (ከ Flask ጋር አብሮ እንዲሰራ)
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()
    
    # Flask ሰርቨሩን በ Render ፖርት ላይ ማስነሳት
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
