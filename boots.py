import os
import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
import telebot
import requests

app = Flask(__name__)
CORS(app)

BOT_TOKEN = "7816393565:AAHUfvHcHYlzRzmcUbuWAbvC2wl1gtkoySM" 
CHANNEL_ID = "-1004333886907"  
ADMIN_CHAT_ID = "8125688786"   

bot = telebot.TeleBot(BOT_TOKEN)
FIREBASE_URL = "https://faf-earning-money-default-rtdb.firebaseio.com"
BOT_USERNAME = "FAF_Earning_money_bot" 
RENDER_URL = "https://faf-earning-money.onrender.com"

def get_user_data(user_id):
    res = requests.get(f"{FIREBASE_URL}/users/{user_id}.json")
    if res.status_code == 200 and res.json():
        return res.json()
    return None

def update_user_data(user_id, data):
    requests.put(f"{FIREBASE_URL}/users/{user_id}.json", json=data)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = str(message.from_user.id)
    username = message.from_user.username or "User"
    text = message.text  
    
    today = datetime.date.today().isoformat()
    user_info = get_user_data(user_id)
    
    if not user_info:
        user_info = {
            "balance": 0.0,
            "ads_count": 0,
            "last_ad_date": today,
            "total_invites": 0,
            "join_date": today,  
            "username": username,
            "profile_complete": False,
            "phone": "",
            "full_name": "",
            "channel_checked": False
        }
        
        if len(text.split()) > 1:
            referrer_id = text.split()[1]
            if referrer_id != user_id:
                ref_data = get_user_data(referrer_id)
                if ref_data:
                    ref_data['balance'] = ref_data.get('balance', 0.0) + 10.0
                    ref_data['total_invites'] = ref_data.get('total_invites', 0) + 1
                    update_user_data(referrer_id, ref_data)
                    try:
                        bot.send_message(referrer_id, f"🎉 አዲስ ሰው ስለጋበዙ +10.00 FAF Coin ወደ አካውንትዎ ተጨምሯል!")
                    except:
                        pass
                        
        update_user_data(user_id, user_info)
    
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    reg_button = telebot.types.KeyboardButton(text="📱 ስልክ ቁጥርህን በቴሌግራም አረጋግጥ (Verify Phone)", request_contact=True)
    markup.add(reg_button)

    welcome_msg = (
        f"👋 እንኳን ወደ FAF Earning Hub በሰላም مጡ!\n\n"
        f"⚠️ ማሳሰቢያ፡ አፑ ላይ የሰሩትን ገንዘብ ወጪ (Withdraw) ለማድረግ መጀመሪያ ከታች ያለውን ሰማያዊ በተን ተጭነው ስልክ ቁጥርዎን ማረጋገጥ አለብዎት!\n\n"
        f"🔗 የእርስዎ መጋበዣ ሊንክ፦\n"
        f"https://t.me/{BOT_USERNAME}?start={user_id}"
    )
    bot.send_message(message.chat.id, welcome_msg, reply_markup=markup)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = str(message.from_user.id)
    contact = message.contact
    
    if str(contact.user_id) != user_id:
        bot.reply_to(message, "❌ ስህተት! እባክዎ የራስዎን ስልክ ቁጥር ያጋሩ።")
        return
        
    user_info = get_user_data(user_id)
    if user_info:
        user_info['phone'] = contact.phone_number
        if user_info.get('full_name'):
            user_info['profile_complete'] = True
        update_user_data(user_id, user_info)
        bot.reply_to(message, f"✅ ስልክ ቁጥርዎ ({contact.phone_number}) በተሳካ ሁኔታ ተረጋግጧል! አሁን በሚኒ አፑ ላይ ሙሉ ስምዎን በመሙላት ስራ መጀመር ይችላሉ።")

# 🔒 ደህንነቱ የተጠበቀ የ AdsGram ማስታወቂያ ማስቆጠሪያ API (ባክኤንድ ጥበቃ)
@app.route('/api/reward-ad', methods=['POST'])
def reward_ad():
    data = request.json
    user_id = str(data.get('user_id'))
    today = datetime.date.today().isoformat()
    
    user_info = get_user_data(user_id)
    if not user_info:
        return jsonify({"success": False, "message": "❌ መጀመሪያ ቦቱ ላይ /start ይበሉ!"}), 404
        
    if user_info.get('last_ad_date') != today:
        user_info['ads_count'] = 0
        user_info['last_ad_date'] = today
        
    if user_info.get('ads_count', 0) >= 15:
        return jsonify({"success": False, "message": "❌ የዕለቱ የ 15 ማስታወቂያ ሊሚትዎን ጨርሰዋል። ነገ ይሞክሩ!"}), 400
        
    user_info['balance'] = user_info.get('balance', 0.0) + 1.50
    user_info['ads_count'] = user_info.get('ads_count', 0) + 1
    update_user_data(user_id, user_info)
    
    return jsonify({"success": True, "balance": user_info['balance'], "ads_count": user_info['ads_count']})

# 👥 የሙሉ ስም እና የሳይለንት ቻናል ቦነስ ማረጋገጫ አንድ ላይ የተዋሃደ API
@app.route('/api/user-info/<user_id>', methods=['GET'])
def get_secure_user_info(user_id):
    user_info = get_user_data(str(user_id))
    if not user_info:
        return jsonify({"error": "User not found"}), 404
        
    # 🤫 ቻናሉን ጆይን ካደረጉ በሳይለንት 0.5 ሳንቲም የመጨመሪያ መስመር
    if not user_info.get('channel_checked', False):
        try:
            member = bot.get_chat_member(CHANNEL_ID, int(user_id))
            if member.status in ['member', 'administrator', 'creator']:
                user_info['balance'] = user_info.get('balance', 0.0) + 0.5
                user_info['channel_checked'] = True
                update_user_data(user_id, user_info)
        except Exception as e:
            print(f"Silent channel check info: {e}")
            
    return jsonify(user_info)

# 🔗 እውነተኛ የ CPA Postback API (CPAGrip እና MyLead 1 ዶላር ሲመጣ 252 FAF Coin የሚያሰላ)
@app.route('/api/postback', methods=['GET', 'POST'])
def cpa_postback():
    user_id = request.args.get('subid') or request.args.get('user_id')
    payout = request.args.get('payout') or request.args.get('amount')
    
    if not user_id or not payout:
        return "Missing Parameters", 400
        
    user_info = get_user_data(str(user_id))
    if user_info:
        reward_coins = float(payout) * 252  
        user_info['balance'] = user_info.get('balance', 0.0) + reward_coins
        update_user_data(user_id, user_info)
        
        try:
            bot.send_message(user_id, f"🔥 ታላቅ ዜና፦ የ CPA ታስክ/ሰርቬይ በተሳካ ሁኔታ ስለጨረሱ +{reward_coins:.2f} FAF Coin ወደ አካውንትዎ ገብቷል!")
        except:
            pass
        return "Success", 200
    return "User not found", 404

@app.route('/api/save-profile', methods=['POST'])
def save_profile():
    data = request.json
    user_id = str(data.get('user_id'))
    full_name = data.get('full_name')
    
    user_info = get_user_data(user_id)
    if not user_info:
        return jsonify({"success": False, "message": "ተጠቃሚ አልተገኘም!"}), 404
        
    user_info['full_name'] = full_name
    if user_info.get('phone'): 
        user_info['profile_complete'] = True
        
    update_user_data(user_id, user_info)
    return jsonify({"success": True, "message": "✅ ሙሉ ስምዎ ተቀምጧል!", "profile_complete": user_info.get('profile_complete', False)})

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
    try:
        bot.remove_webhook()
        bot.set_webhook(url=f"{RENDER_URL}/{BOT_TOKEN}")
        return "FAF Hub Server is running beautifully with full CPA & Security setup!"
    except Exception as e:
        return f"Webhook error: {e}", 500

@app.route('/api/daily-bonus', methods=['POST'])
def daily_bonus():
    data = request.json
    user_id = str(data.get('user_id'))
    today = datetime.date.today().isoformat()
    
    user_info = get_user_data(user_id)
    if not user_info:
        return jsonify({"success": False, "message": "❌ መጀመሪያ ቦቱ ላይ /start ይበሉ!"}), 404
    
    if user_info.get('last_bonus') == today:
        return jsonify({"success": False, "message": "❌ ለዛሬ ወስደሃል። ነገ ተመለስ!"}), 400
        
    user_info['balance'] = user_info.get('balance', 0.0) + 4.0
    user_info['last_bonus'] = today
    update_user_data(user_id, user_info)
    return jsonify({"success": True, "message": "🎁 ✅ የዛሬው 4.00 FAF Coins ቦነስዎ ተጨምሯል!"})

@app.route('/api/withdraw', methods=['POST'])
def withdraw():
    data = request.json
    user_id = str(data.get('user_id'))
    method = data.get('method')
    account = data.get('account')
    holder_name = data.get('holder_name')
    coin_amount = float(data.get('amount', 400)) 
    
    user_info = get_user_data(user_id)
    if not user_info:
        return jsonify({"success": False, "message": "❌ ተጠቃሚ አልተገኘም!"}), 404
        
    if not user_info.get('profile_complete'):
        return jsonify({
            "success": False, 
            "message": "❌ የደህንነት ስህተት! እባክዎ መጀመሪያ ስልክ ቁጥርዎን በቦቱ ላይ ያረጋግጡ እና ሚኒ አፑ ላይ ሙሉ ስምዎን ይሙሉ!"
        }), 403
        
    current_balance = user_info.get('balance', 0.0)
    if current_balance < coin_amount:
        return jsonify({"success": False, "message": "❌ በቂ ሳንቲም የለዎትም!"}), 400

    msg_text = (
        f"💰 *አዲስ የክፍያ ጥያቄ (Verified Profile)*\n\n"
        f"👤 የተጠቃሚ ID: `{user_id}`\n"
        f"📞 የተረጋገጠ ስልክ: `{user_info.get('phone')}`\n"
        f"📝 እውነተኛ ስም: {user_info.get('full_name')}\n"
        f"🏦 የክፍያ መንገድ: {method.upper()}\n"
        f"💳 አካውንት/ስልክ ቁጥር: `{account}`\n"
        f"💵 የተዋጣ መጠን: {coin_amount} FAF Coins\n"
    )
    
    try:
        bot.send_message(CHANNEL_ID, msg_text, parse_mode="Markdown")
        bot.send_message(ADMIN_CHAT_ID, f"🔔 አዲስ ትዕዛዝ መጥቷል! ከ {user_info.get('full_name')}")
        
        user_info['balance'] = current_balance - coin_amount
        update_user_data(user_id, user_info)
        return jsonify({"success": True, "message": "✅ የክፍያ ጥያቄዎ በተሳካ ሁኔታ ተልኳል!"})
    except Exception as e:
        return jsonify({"success": False, "message": f"❌ ስህተት ተከስቷል፦ {e}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
