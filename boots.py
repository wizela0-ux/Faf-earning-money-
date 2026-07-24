import os
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
import requests

app = Flask(__name__)
CORS(app)

# --- 1. አንተ የሰጠኸኝ ትክክለኛ መረጃዎች ማዋቀሪያ ---
BOT_TOKEN = "8366647485:AAFZbHSaLgVGCBNw2PiS2LpEnphFv9MAeMU" 
CHANNEL_ID = "-1004333886907"  # የክፍያ ጥያቄዎች የሚላኩበት ቻናል ID
ADMIN_CHAT_ID = "8125688786"   # ያንተ የግል ቴሌግራም ID

bot = telebot.TeleBot(BOT_TOKEN)

# የ Firebase Realtime Database ዋና ሊንክህ
FIREBASE_URL = "https://faf-earning-money-default-rtdb.firebaseio.com"
# የቦትህ ትክክለኛው ዩዘርኔም (ያለ @ ምልክት)
BOT_USERNAME = "FAF_Earning_money_bot" 
# ያንተ የ Render ዋና ድህረ-ገጽ ሊንክ
RENDER_URL = "https://faf-earning-money.onrender.com"

# --- 2. የ Firebase መረጃ ማንበቢያ እና መፃፊያ ረዳት ፈንክሽኖች ---
def get_user_data(user_id):
    res = requests.get(f"{FIREBASE_URL}/users/{user_id}.json")
    if res.status_code == 200 and res.json():
        return res.json()
    return None

def update_user_data(user_id, data):
    requests.put(f"{FIREBASE_URL}/users/{user_id}.json", json=data)

# --- 3. ቴሌግራም ላይ ሰው /start ሲል የሚመዘገብበት ዋናው ክፍል ---
@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "User"
    text = message.text  # ይህ /start 1234567 የተባለውን የጋባዥ ID ይይዛል
    
    today = datetime.date.today().isoformat()
    user_info = get_user_data(user_id)
    
    # 🎯 ተጠቃሚው በዴታቤዙ ውስጥ ከሌለ (ፍጹም አዲስ ሰው ከሆነ) ብቻ ይመዘገባል
    if not user_info:
        user_info = {
            "balance": 0.0,
            "ads_count": 0,
            "total_invites": 0,
            "join_date": today,  # 👈 ለታስኮች መክፈቻ ዋናው ወሳኝ መረጃ!
            "username": username
        }
        
        # 🔗 ሰውየው በሪፈራል ሊንክ የመጣ ከሆነ እና ራሱን ካልጋበዘ
        if len(text.split()) > 1:
            referrer_id = text.split()[1]
            if referrer_id != user_id:
                ref_data = get_user_data(referrer_id)
                if ref_data:
                    # ለጋባዡ +5.00 ETB እና 1 ሪፈራል እንጨምራለን
                    ref_data['balance'] = ref_data.get('balance', 0.0) + 5.0
                    ref_data['total_invites'] = ref_data.get('total_invites', 0) + 1
                    update_user_data(referrer_id, ref_data)
                    
                    try:
                        bot.send_message(referrer_id, f"🎉 አዲስ ሰው ስለጋበዙ +5.00 ETB ወደ አካውንትዎ ተጨምሯል!")
                    except:
                        pass
                        
        update_user_data(user_id, user_info)
    
    # ለሰውየው ወደ አፑ መግቢያ እና የራሱን መጋበዣ ሊንክ መላክ
    welcome_msg = (
        f"👋 እንኳን ወደ FAF Earning Hub በሰላም መጡ!\n\n"
        f"ከታች ያለውን ሊንክ በመጫን በቀላሉ ማስታወቂያዎችን በማየት እና ታስኮችን በመስራት ገንዘብ ማግኘት ይጀምሩ።\n\n"
        f"🔗 የእርስዎ መጋበዣ ሊንክ፦\n"
        f"https://t.me/{BOT_USERNAME}?start={user_id}"
    )
    bot.reply_to(message, welcome_msg)

# --- 4. የዌብሁክ መቀበያ መስመሮች (API Routes) ---
@app.route('/' + BOT_TOKEN, methods=['POST'])
def getMessage():
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return "OK", 200
    return "Forbidden", 403

@app.route('/')
def home():
    # ሰርቨሩ በብሮውዘር ሲከፈት ዌብሁኩን በራስ-ሰር ቴሌግራም ላይ ይቆልፈዋል
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
        return "FAF Hub Server with Webhook is active and running beautifully!"
    except Exception as e:
        return f"Webhook error: {e}", 500

# --- 5. የ FAF Coin ዕለታዊ ቦነስ API ---
@app.route('/api/daily-bonus', methods=['POST'])
def daily_bonus():
    data = request.json
    user_id = str(data.get('user_id'))
    today = datetime.date.today().isoformat()
    
    user_info = get_user_data(user_id)
    if not user_info:
        return jsonify({"success": False, "message": "❌ ተጠቃሚው አልተገኘም። በመጀመሪያ ቦቱ ላይ /start ይበሉ!"}), 404
    
    if user_info.get('last_bonus') == today:
        return jsonify({
            "success": False, 
            "message": "❌ ለዛሬ የ FAF Coin ቦነስህን ወስደሃል። እባክህ ነገ ተመለስ!"
        }), 400
        
    user_info['balance'] = user_info.get('balance', 0.0) + 4.0
    user_info['last_bonus'] = today
    
    update_user_data(user_id, user_info)
    
    return jsonify({
        "success": True, 
        "message": "🎁 ✅ የዛሬው 4.00 FAF Coins ቦነስዎ ተጨምሯል!", 
        "new_balance": user_info['balance']
    })

# --- 6. የክፍያ መጠየቂያ (Withdraw) API ---
@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    user_id = str(data.get('user_id'))
    method = data.get('method')
    account = data.get('account')
    holder_name = data.get('holder_name')
    coin_amount = float(data.get('amount', 200)) 
    
    user_info = get_user_data(user_id)
    if not user_info:
        return jsonify({"success": False, "message": "❌ ተጠቃሚ አልተገኘም!"}), 404
        
    current_balance = user_info.get('balance', 0.0)
    
    if current_balance < coin_amount:
        return jsonify({
            "success": False,
            "message": f"❌ በቂ ኮይን የለዎትም! ቢያንስ {coin_amount} FAF Coins ያስፈልጋል።"
        }), 400

    if method in ['telebirr', 'cbe', 'awash']:
        msg_text = (
            f"💰 *አዲስ የባንክ/ቴሌብር ክፍያ ጥያቄ*\n\n"
            f"👤 የተጠቃሚ ID: `{user_id}`\n"
            f"🏦 የክፍያ መንገድ: {method.upper()}\n"
            f"👤 የባለቤቱ ስም: {holder_name}\n"
            f"💳 አካውንት/ስልክ ቁጥር: `{account}`\n"
            f"💵 የተዋጣ መጠን: {coin_amount} ETB\n"
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
            f"🎁 የሚሞላው: {reward}\n"
            f"💵 የወጣው ወጪ: {coin_amount} ETB\n"
            f"🔐 ፒን ኮድ: የተረጋገጠ\n"
            f"⏰ ቀን: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    
    try:
        # ወደ ቻናሉ መላክ
        bot.send_message(CHANNEL_ID, msg_text, parse_mode="Markdown")
        # ላንተ ለአድሚኑ ኖቲፊኬሽን መላክ
        bot.send_message(ADMIN_CHAT_ID, f"🔔 አዲስ ትዕዛዝ መጥቷል! አይነት: {method}፣ መጠን: {coin_amount} ETB")
        
        user_info['balance'] = current_balance - coin_amount
        update_user_data(user_id, user_info)
        
        return jsonify({
            "success": True, 
            "message": "✅ የክፍያ ጥያቄዎ በተሳካ ሁኔታ ተልኳል! በአስተዳዳሪው ተገምግሞ ይላካል።"
        })
    except Exception as e:
        return jsonify({
            "success": False, 
            "message": "❌ አልተላከም! የሲስተም መቆራረጥ አጋጥሟል፣ እባክዎ ድጋሚ ይሞክሩ።"
        }), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
