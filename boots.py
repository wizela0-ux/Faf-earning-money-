import os
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
import requests

app = Flask(__name__)
CORS(app)

# --- እነዚህን መረጃዎች በራስህ መረጃዎች ተካ ---
BOT_TOKEN = "የአንተ_ትክክለኛ_የቦት_ቶክን"  # ከ BotFather ያገኘኸው
CHANNEL_ID = "@የአንተ_ቻናል_ዩዘርኔም"      # ለምሳሌ: @faf_earning
ADMIN_CHAT_ID = "የአንተ_ቴሌግራም_ID"     # ያንተ የግል ቴሌግራም ID ቁጥር

bot = telebot.TeleBot(BOT_TOKEN)

# የ Firebase Realtime Database ሊንክህ
FIREBASE_URL = "https://faf-earning-money-default-rtdb.firebaseio.com/"

def get_user_data(user_id):
    res = requests.get(f"{FIREBASE_URL}/users/{user_id}.json")
    if res.status_code == 200 and res.json():
        return res.json()
    return {"balance": 0.0, "last_bonus": ""}

def update_user_data(user_id, data):
    requests.put(f"{FIREBASE_URL}/users/{user_id}.json", json=data)

@app.route('/')
def home():
    return "FAF Hub Server with Firebase is active and running beautifully!"

# 1. የ FAF Coin ዕለታዊ ቦነስ መቆለፊያ ህግ (በ 24 ሰአት አንድ ጊዜ)
@app.route('/api/daily-bonus', methods=['POST'])
def daily_bonus():
    data = request.json
    user_id = str(data.get('user_id'))
    today = datetime.date.today().isoformat()
    
    user_info = get_user_data(user_id)
    
    if user_info.get('last_bonus') == today:
        return jsonify({
            "success": False, 
            "message": "❌ ለዛሬ የ FAF Coin ቦነስህን ወስደሃል። እባክህ ነገ ተመለስ!"
        }), 400
        
    # በኮይን ስሌት መሠረት 2 FAF Coins (የ 1 ብር ዋጋ) እንሰጣለን
    user_info['balance'] = user_info.get('balance', 0.0) + 2.0
    user_info['last_bonus'] = today
    
    update_user_data(user_id, user_info)
    
    return jsonify({
        "success": True, 
        "message": "🎁 ✅ የዛሬው 2.00 FAF Coins ቦነስዎ ተጨምሯል!", 
        "new_balance": user_info['balance']
    })

# 2. የክፍያ መጠየቂያ (Withdraw) - በባንክ፣ PUBG UC ወይም Free Fire 
@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    user_id = str(data.get('user_id'))
    method = data.get('method') # 'bank', 'pubg', 'ff'
    account = data.get('account')
    holder_name = data.get('holder_name')
    pin_code = data.get('pin_code')
    coin_amount = float(data.get('amount', 400)) # 400 ኮይን ለ 60 UC
    
    user_info = get_user_data(user_id)
    current_balance = user_info.get('balance', 0.0)
    
    if current_balance < coin_amount:
        return jsonify({
            "success": False,
            "message": f"❌ በቂ ኮይን የለዎትም! ቢያንስ {coin_amount} FAF Coins ያስፈልጋል።"
        }), 400

    # የመልእክት አይነትን ማስተካከል
    if method == 'bank':
        msg_text = (
            f"💰 *አዲስ የባንክ ክፍያ ጥያቄ*\n\n"
            f"👤 የተጠቃሚ ID: `{user_id}`\n"
            f"👤 የባለቤቱ ስም: {holder_name}\n"
            f"💳 የባንክ/ቴሌብር አካውንት: `{account}`\n"
            f"💵 የተዋጣ መጠን: {coin_amount} FAF Coins\n"
            f"🔐 ፒን ኮድ: የተረጋገጠ\n"
            f"⏰ ቀን: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    else:
        game_name = "PUBG UC" if method == 'pubg' else "Free Fire Diamond"
        reward = "60 UC" if method == 'pubg' else "50 Diamonds"
        msg_text = (
            f"🎮 *አዲስ የጌም ቶፕ-አፕ ጥያቄ ({game_name})*\n\n"
            f"👤 የተጠቃሚ ID: `{user_id}`\n"
            f"🆔 የጌም Player ID: `{account}`\n"
            f"👤 የጌም ስም: {holder_name}\n"
            f"🎁 የሚሞላው: {reward}\n"
            f"💵 የወጣው ወጪ: {coin_amount} FAF Coins\n"
            f"🔐 ፒን ኮድ: የተረጋገጠ\n"
            f"⏰ ቀን: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    
    try:
        # ሰርቨሩ መጀመሪያ ወደ አንተ ቻናል መላኩን ያረጋግጣል
        bot.send_message(CHANNEL_ID, msg_text, parse_mode="Markdown")
        bot.send_message(ADMIN_CHAT_ID, f"🔔 አዲስ ትዕዛዝ መጥቷል! አይነት: {method}፣ ስም: {holder_name}")
        
        # የሰውየውን ኮይን ቀንሰን Firebase ላይ ሴቭ እናደርጋለን
        user_info['balance'] = current_balance - coin_amount
        update_user_data(user_id, user_info)
        
        return jsonify({
            "success": True, 
            "message": "✅ የክፍያ ጥያቄዎ በተሳካ ሁኔታ ተልኳል! በ 10 ሰከንዶች ውስጥ ይፈጸማል።"
        })
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": "❌ አልተላከም! የሲስተም መቆራረጥ አጋጥሟል፣ እባክዎ ድጋሚ ይሞክሩ።"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
