import requests
import json
import datetime
import re
import pytz
import asyncio
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# --- Configuration ---
ADMIN_ID = 1694027441
TOKEN = "8590048565:AAECrq8MHjiul5aLjWbsnqCZNzyI9TgthOc"
SUPABASE_URL = "https://pzzfhhpiygqdnrallztv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InB6emZoaHBpeWdxZG5yYWxsenR2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkwMDQ4MDksImV4cCI6MjA4NDU4MDgwOX0.c0Ts-4j09afr8_t-hp7brfFjWAwQviPiNjoU7Jr4rps"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "Prefer": "return=minimal"
}

# States
STEP_FB_TG, STEP_ADDRESS, STEP_MASTER = range(3)
STEP_WAIT_IDS, STEP_WAIT_REASON = range(3, 5)
STEP_BROADCAST = 5
STEP_CHANGE_CONTACT = 6

# --- Database Functions ---

def get_admin_contact():
    url = f"{SUPABASE_URL}/rest/v1/settings?key=eq.admin_link&select=value"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        return data[0]['value'] if data else "https://t.me/shehateme1"
    except: return "https://t.me/shehateme1"

def set_admin_contact(new_link):
    url = f"{SUPABASE_URL}/rest/v1/settings?key=eq.admin_link"
    payload = {"value": new_link}
    try: requests.patch(url, headers=HEADERS, json=payload, timeout=10)
    except: pass

def is_approved(user_id):
    if user_id == ADMIN_ID: return True
    url = f"{SUPABASE_URL}/rest/v1/whitelist?user_id=eq.{user_id}&select=*"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        return len(resp.json()) > 0
    except: return False

def get_all_users():
    url = f"{SUPABASE_URL}/rest/v1/whitelist?select=user_id"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        return [str(row['user_id']) for row in resp.json()]
    except: return []

def check_blacklist(target_id):
    url = f"{SUPABASE_URL}/rest/v1/blacklist_records?target_id=eq.{target_id}&select=*"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10)
        data = resp.json()
        return data[0] if data else None
    except: return None

# --- Keyboard Setup ---
def get_main_keyboard(user_id):
    if user_id == ADMIN_ID:
        keyboard = [['🔍 ID စစ်ဆေးရန်'], ['➕ ID အသစ်ထည့်ရန်', '📢 Users သို့စာပို့'], ['⚙️ Admin Contact ပြောင်းရန်']]
    else:
        keyboard = [['🔍 ID စစ်ဆေးရန်'], ['➕ ID အသစ်ထည့်ရန်', '📞 Admin သို့ဆက်သွယ်ရန်']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if is_approved(user_id):
        await update.message.reply_text("✅ <b>Bot ကို အသုံးပြုနိုင်ပါပြီ။</b>", reply_markup=get_main_keyboard(user_id), parse_mode='HTML')
        return ConversationHandler.END
    
    msg = (
        "<b>မင်္ဂလာပါ</b> 👋\n\n"
        "Agent ဖြစ်ကြောင်းအတည်ပြုနိုင်ရန် အချက်အလက်ဖြည့်သွင်းဖို့ လိုအပ်ပါသည် ။\n\n"
        "သင်၏ <b>Facebook acc name</b> သို့မဟုတ် <b>Telegram username</b> ကို ပို့ပေးပါ။"
    )
    await update.message.reply_text(msg, parse_mode='HTML')
    return STEP_FB_TG

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    await update.message.reply_text("🚫 <b>လုပ်ဆောင်ချက်ကို ပယ်ဖျက်လိုက်ပါပြီ။</b>", reply_markup=get_main_keyboard(user_id), parse_mode='HTML')
    return ConversationHandler.END

# --- Registration Flow ---
async def get_fb_tg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['fb_tg'] = update.message.text
    await update.message.reply_text("✅ <b>Acc Name ရရှိပါသည်</b>\n\nသင်၏ Agent Address / Withdraw address ကို ဆက်လက်ပေးပို့ပါ ။\n\n/cancel", parse_mode='HTML')
    return STEP_ADDRESS

async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['address'] = update.message.text
    await update.message.reply_text("✅ <b>Agent Address ရရှိပါသည်။</b>\n\nသင်၏ Master Name ကို ဆက်လက်ပေးပို့ပါ။\n\n/cancel", parse_mode='HTML')
    return STEP_MASTER

async def get_master_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    kb = [[InlineKeyboardButton("✅ Accept", callback_data=f"acc_{user_id}"), InlineKeyboardButton("❌ Decline", callback_data=f"dec_{user_id}")]]
    
    admin_msg = (
        "📩 <b>လျှောက်လွှာအသစ် ရရှိသည်</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🔗 FB/TG: {context.user_data['fb_tg']}\n"
        f"🏠 Addr: {context.user_data['address']}\n"
        f"👑 Master: {update.message.text}"
    )
    
    await context.bot.send_message(chat_id=ADMIN_ID, text=admin_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
    await update.message.reply_text("✅ <b>အချက်အလက်များ လက်ခံရရှိပါသည်။</b>\n\nသင်၏တောင်းဆိုမှုကို Admin ထံသို့ပေးပို့ထားပါသည်။ ခေတ္တစောင့်ဆိုင်းပေးပါ။", parse_mode='HTML')
    return ConversationHandler.END

# --- Main Logic ---
async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    
    if not is_approved(user_id): return

    if text == "🔍 ID စစ်ဆေးရန်":
        await update.message.reply_text("🔢 <b>စစ်ဆေးလိုသော ID နံပါတ်ကို ရိုက်ပို့ပေးပါ။</b>\n\n/cancel", parse_mode='HTML')
        return
    if text == "➕ ID အသစ်ထည့်ရန်":
        await update.message.reply_text("🚫 <b>Blacklist သွင်းမည့် ID များကို ပို့ပေးပါ။</b>\n\n(ID တစ်ခုထက်ပိုလျှင် Space သို့မဟုတ် Enter ခြားပြီး ပို့နိုင်သည်)\n\n/cancel", parse_mode='HTML')
        return STEP_WAIT_IDS
    if text == "📢 Users သို့စာပို့" and user_id == ADMIN_ID:
        await update.message.reply_text("📣 <b>User များသို့ ပို့လိုသော စာကို ရိုက်ထည့်ပါ။</b>\n\n/cancel", parse_mode='HTML')
        return STEP_BROADCAST
    if text == "⚙️ Admin Contact ပြောင်းရန်" and user_id == ADMIN_ID:
        await update.message.reply_text("🔗 <b>Link အသစ်ပို့ပေးပါ။</b>\n(ဥပမာ- https://t.me/username)\n\n/cancel", parse_mode='HTML')
        return STEP_CHANGE_CONTACT
    if text == "📞 Admin သို့ဆက်သွယ်ရန်":
        link = get_admin_contact()
        await update.message.reply_text(f"👨‍💻 <b>Admin သို့ ဆက်သွယ်ရန်</b>\n\n👇👇👇\n{link}", parse_mode='HTML')
        return

    if text and text.isdigit():
        bl_data = check_blacklist(text)
        if bl_data:
            result = (
                "🚫 <b>Blacklist ID တွေ့ရှိသည်</b>\n\n"
                f"📌 ID: <code>{text}</code>\n"
                f"📅 ရက်စွဲ: {bl_data['date']}\n"
                f"📝 အကြောင်းရင်း: {bl_data['reason']}\n\n"
                "⚠️ သတိထား ဆက်ဆံပေးပါရန်။"
            )
            await update.message.reply_text(result, parse_mode='HTML')
        else:
            await update.message.reply_text(f"✅ <b>စိတ်ချရပါသည်</b>\n\nယခု Id (<code>{text}</code>) သည် Blacklist စာရင်းတွင် မရှိပါ။", parse_mode='HTML')

async def process_ids(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ids = re.split(r'[\s,\n]+', update.message.text.strip())
    context.user_data['pending_ids'] = ids
    await update.message.reply_text(f"📥 <b>ID ({len(ids)}) ခု ရရှိပါသည်။</b>\n\nယခု ID များအတွက် <b>အကြောင်းပြချက် (Reason)</b> ကို ပို့ပေးပါ။\n\n/cancel", parse_mode='HTML')
    return STEP_WAIT_REASON

async def process_reason(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason = update.message.text
    ids = context.user_data.get('pending_ids', [])
    sender_name = update.message.from_user.first_name
    sender_id = update.message.from_user.id
    now = datetime.datetime.now(pytz.timezone('Asia/Yangon')).strftime("%d-%m-%Y %I:%M %p")
    
    await update.message.reply_text("⏳ <b>Database သို့ သိမ်းဆည်းနေပါသည်...</b>", parse_mode='HTML')

    for target_id in ids:
        if target_id:
            try:
                payload = {"target_id": str(target_id), "reporter": sender_name, "reason": reason, "date": now}
                requests.post(f"{SUPABASE_URL}/rest/v1/blacklist_records", headers=HEADERS, json=payload, timeout=10)
            except: continue
    
    id_list_str = "\n- ".join(ids)
    
    # User အားလုံးဆီ ပို့မည့် format (ရှင်းလင်းအောင် ပြင်ထားသည်)
    notif_text = (
        "📢 <b>Blacklist ID အသစ် တင်လိုက်ပါပြီ</b>\n\n"
        f"👤 တင်သူ: <b>{sender_name}</b>\n"
        f"📅 အချိန်: {now}\n\n"
        f"📌 <b>ID စာရင်း:</b>\n- {id_list_str}\n\n"
        f"📝 <b>အကြောင်းရင်း:</b>\n{reason}"
    )

    # 1. Admin ဆီသို့ Notification ပို့ခြင်း
    if sender_id != ADMIN_ID:
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ <b>Admin Notification</b>\n\n{notif_text}", parse_mode='HTML')
        except: pass

    # 2. Users အားလုံးဆီသို့ Notification ပို့ခြင်း
    users = get_all_users()
    for user in users:
        try:
            if int(user) != sender_id: 
                await context.bot.send_message(chat_id=int(user), text=notif_text, parse_mode='HTML')
                await asyncio.sleep(0.3)
        except: continue
    
    # 3. တင်တဲ့ User ကိုယ်တိုင်ဆီ အောင်မြင်ကြောင်း ပြန်ပို့ခြင်း
    await update.message.reply_text(
        "✅ <b>အောင်မြင်စွာ တင်ပြီးပါပြီ</b>\n\n"
        "သင်၏ Blacklist တင်မှုကို User အားလုံးဆီသို့ အသိပေးချက် ပို့ပြီးပါပြီ။",
        reply_markup=get_main_keyboard(sender_id),
        parse_mode='HTML'
    )
    return ConversationHandler.END

async def process_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    users = get_all_users()
    count = 0
    await update.message.reply_text(f"🚀 လူပေါင်း {len(users)} ဦးထံသို့ စာစတင်ပို့နေပါပြီ...")
    for i, user in enumerate(users):
        try:
            await context.bot.send_message(chat_id=int(user), text=f"🔔 <b>သတင်းစကား</b>\n\n{text}", parse_mode='HTML')
            count += 1
            if (i + 1) % 25 == 0: await asyncio.sleep(1)
        except: continue
    await update.message.reply_text(f"✅ <b>စာပို့ခြင်း ပြီးဆုံးပါပြီ။</b>\n\nပေးပို့ပြီးအရေအတွက်: ({count}) ဦး", reply_markup=get_main_keyboard(ADMIN_ID), parse_mode='HTML')
    return ConversationHandler.END

async def process_change_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_link = update.message.text.strip()
    set_admin_contact(new_link)
    await update.message.reply_text(f"✅ <b>Admin Contact ပြောင်းလဲပြီးပါပြီ။</b>\n\nLink အသစ်: {new_link}", reply_markup=get_main_keyboard(ADMIN_ID), parse_mode='HTML')
    return ConversationHandler.END

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split("_")
    if data[0] == "acc":
        user_id = int(data[1])
        payload = {"user_id": user_id, "status": "approved"}
        requests.post(f"{SUPABASE_URL}/rest/v1/whitelist", headers=HEADERS, json=payload, timeout=10)
        await query.edit_message_text(f"✅ <b>ID: {user_id} ကို ခွင့်ပြုလိုက်ပါပြီ။</b>", parse_mode='HTML')
        try:
            welcome_msg = (
                "ဂုဏ်ယူပါတယ် 🥳\n\n"
                "သင်၏ Bot အသုံးပြုခွင့်ကို <b>Approve</b> လုပ်ပြီးပါပြီ ။\n\n"
                "/start ကိုနှိပ်ပြီး စတင် အသုံးပြုနိုင်ပါပြီ ။"
            )
            await context.bot.send_message(chat_id=user_id, text=welcome_msg, reply_markup=get_main_keyboard(user_id), parse_mode='HTML')
        except: pass
    elif data[0] == "dec":
        await query.edit_message_text(f"❌ <b>ID: {data[1]} ကို ငြင်းပယ်လိုက်ပါပြီ။</b>", parse_mode='HTML')

def main():
    while True:
        try:
            app = Application.builder().token(TOKEN).build()
            conv_handler = ConversationHandler(
                entry_points=[
                    CommandHandler("start", start),
                    MessageHandler(filters.Text(["🔍 ID စစ်ဆေးရန်", "➕ ID အသစ်ထည့်ရန်", "📢 Users သို့စာပို့", "⚙️ Admin Contact ပြောင်းရန်"]), handle_main_menu)
                ],
                states={
                    STEP_FB_TG: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fb_tg)],
                    STEP_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
                    STEP_MASTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_master_name)],
                    STEP_WAIT_IDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_ids)],
                    STEP_WAIT_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_reason)],
                    STEP_BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_broadcast)],
                    STEP_CHANGE_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_change_contact)],
                },
                fallbacks=[CommandHandler("cancel", cancel)],
            )
            app.add_handler(conv_handler)
            app.add_handler(CallbackQueryHandler(button_callback))
            app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu))
            
            print("🚀 Bot is running...")
            app.run_polling(drop_pending_updates=True)
        except Exception as e:
            print(f"Error: {e}. Restarting in 5s...")
            time.sleep(5)

if __name__ == '__main__':
    main()
