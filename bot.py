import telebot
from telebot import types
import config
import database as db
import logging
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML")
admin_states = {}

def is_admin(user_id):
    return user_id == config.ADMIN_ID

@bot.message_handler(commands=['start'])
def send_welcome(message):
    db.init_db()
    first_name = message.from_user.first_name
    welcome_text = db.get_setting('welcome_text') or "Welcome to our Premium Service! 🚀"
    formatted_msg = f"✨ <b>Hello, {first_name}!</b>\n\n{welcome_text}"
    
    start_image = db.get_setting('start_image')
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("👇 Choose A Plan", callback_data="view_plans"))
    
    if start_image:
        try:
            bot.send_photo(message.chat.id, start_image, caption=formatted_msg, reply_markup=markup)
        except Exception:
            bot.send_message(message.chat.id, formatted_msg, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, formatted_msg, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "view_plans")
def user_view_plans(call):
    plans = db.get_plans()
    if not plans:
        bot.answer_callback_query(call.id, "❌ No premium plans available yet.")
        return
        
    markup = types.InlineKeyboardMarkup(row_width=1)
    for p in plans:
        btn_text = f"💎 {p[1]} - ₹{p[2]} ({p[3]})"
        markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"u_plan_{p[0]}"))
        
    bot.edit_message_text("🌟 <b>Available Premium Plans:</b>\nSelect a plan to inspect content and purchase.", 
                          call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("u_plan_"))
def user_inspect_plan(call):
    plan_id = int(call.data.split("_")[2])
    plan = db.get_plan(plan_id)
    if not plan:
        bot.answer_callback_query(call.id, "Plan no longer exists.")
        return
        
    media_items = db.get_plan_media(plan_id)
    if media_items:
        bot.send_message(call.message.chat.id, "📦 <b>Previewing Plan Content Assets Below:</b>")
        for item in media_items:
            file_id, media_type = item[0], item[1]
            try:
                if media_type == 'photo':
                    bot.send_photo(call.message.chat.id, file_id)
                elif media_type == 'video':
                    bot.send_video(call.message.chat.id, file_id)
            except Exception:
                pass
                
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🛍️ Buy Plan Now", callback_data=f"buy_plan_{plan_id}"))
    markup.add(types.InlineKeyboardButton("🔙 Back to Plans", callback_data="view_plans"))
    
    msg_text = f"💎 <b>Plan:</b> {plan[1]}\n💰 <b>Price:</b> ₹{plan[2]}\n⏳ <b>Validity:</b> {plan[3]}"
    bot.send_message(call.message.chat.id, msg_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("buy_plan_"))
def checkout_plan(call):
    plan_id = int(call.data.split("_")[2])
    plan = db.get_plan(plan_id)
    qr_code = db.get_setting('qr_code')
    upi_id = db.get_setting('upi_id') or "Not configured by admin"
    
    instruction = (
        f"💳 <b>Checkout Order Summary:</b>\n\n"
        f"📦 <b>Plan:</b> {plan[1]}\n"
        f"💰 <b>Amount Due:</b> ₹{plan[2]}\n"
        f"⏳ <b>Validity:</b> {plan[3]}\n\n"
        f"🔑 <b>UPI ID:</b> <code>{upi_id}</code>\n\n"
        f"⚠️ <i>Scan the QR or copy the UPI ID to make payment. Once completed, click the button below to submit your receipt.</i>"
    )
    
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✅ VERIFY PAYMENT", callback_data=f"verify_pay_{plan_id}"))
    
    if qr_code:
        try:
            bot.send_photo(call.message.chat.id, qr_code, caption=instruction, reply_markup=markup)
        except Exception:
            bot.send_message(call.message.chat.id, instruction, reply_markup=markup)
    else:
        bot.send_message(call.message.chat.id, instruction, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("verify_pay_"))
def verify_payment_request(call):
    plan_id = call.data.split("_")[2]
    msg = bot.send_message(call.message.chat.id, "📸 Please upload and send your <b>Payment Screenshot</b> now:")
    bot.register_next_step_handler(msg, process_payment_screenshot, plan_id)

def process_payment_screenshot(message, plan_id):
    if not message.photo:
        bot.reply_to(message, "❌ Invalid input. Please click 'VERIFY PAYMENT' again and upload an image screenshot.")
        return
        
    plan = db.get_plan(int(plan_id))
    file_id = message.photo[-1].file_id
    
    bot.send_message(message.chat.id, "⏳ Your receipt has been sent to admin verification team. Please await activation.")
    
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(
        types.InlineKeyboardButton("✅ Approve", callback_data=f"adm_app_{message.from_user.id}_{plan_id}"),
        types.InlineKeyboardButton("❌ Reject", callback_data=f"adm_rej_{message.from_user.id}_{plan_id}")
    )
    
    admin_info = (
        f"💰 <b>New Payment Verification Request</b>\n\n"
        f"👤 <b>User Name:</b> {message.from_user.first_name}\n"
        f"🆔 <b>User ID:</b> <code>{message.from_user.id}</code>\n"
        f"📦 <b>Selected Plan:</b> {plan[1]}\n"
        f"💵 <b>Price Amount:</b> ₹{plan[2]}"
    )
    bot.send_photo(config.ADMIN_ID, file_id, caption=admin_info, reply_markup=admin_markup)

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    if not is_admin(message.from_user.id):
        return
    show_admin_menu(message.chat.id)

def show_admin_menu(chat_id):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🖼 Set Start Image", callback_data="adm_cfg_image"),
        types.InlineKeyboardButton("📝 Set Welcome Text", callback_data="adm_cfg_text"),
        types.InlineKeyboardButton("📦 Add Plans", callback_data="adm_cfg_addplan"),
        types.InlineKeyboardButton("📋 Manage Plans", callback_data="adm_cfg_manplan"),
        types.InlineKeyboardButton("📷 Set QR Code", callback_data="adm_cfg_qr"),
        types.InlineKeyboardButton("💳 Set UPI ID", callback_data="adm_cfg_upi")
    )
    bot.send_message(chat_id, "⚙️ <b>Premium Bot Admin Control Dashboard</b>", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("adm_"))
def admin_actions(call):
    if not is_admin(call.from_user.id):
        return
        
    action = call.data
    
    if action == "adm_cfg_image":
        msg = bot.send_message(call.message.chat.id, "🖼 Please upload the new start banner image:")
        bot.register_next_step_handler(msg, save_start_image)
    elif action == "adm_cfg_text":
        msg = bot.send_message(call.message.chat.id, "📝 Please type your custom welcome greeting message text:")
        bot.register_next_step_handler(msg, save_welcome_text)
    elif action == "adm_cfg_qr":
        msg = bot.send_message(call.message.chat.id, "📷 Upload your static checkout merchant QR Code image:")
        bot.register_next_step_handler(msg, save_qr_code)
    elif action == "adm_cfg_upi":
        msg = bot.send_message(call.message.chat.id, "💳 Write down your targeted configuration corporate UPI ID:")
        bot.register_next_step_handler(msg, save_upi_id)
    elif action == "adm_cfg_addplan":
        msg = bot.send_message(call.message.chat.id, "🏷 Enter Plan Title Name:")
        bot.register_next_step_handler(msg, process_plan_name)
    elif action == "adm_cfg_manplan":
        plans = db.get_plans()
        if not plans:
            bot.send_message(call.message.chat.id, "❌ Database has no current subscription packages active.")
            return
        for p in plans:
            m = types.InlineKeyboardMarkup()
            m.add(
                types.InlineKeyboardButton("🔗 Set Delivery Link", callback_data=f"adm_link_{p[0]}"),
                types.InlineKeyboardButton("➕ Add Content Media", callback_data=f"adm_media_{p[0]}"),
                types.InlineKeyboardButton("🗑 Delete Plan", callback_data=f"adm_del_{p[0]}")
            )
            bot.send_message(call.message.chat.id, f"📦 <b>Plan Profile ID:</b> #{p[0]}\n🏷 <b>Name:</b> {p[1]}\n💵 <b>Price:</b> ₹{p[2]}\n⏳ <b>Validity:</b> {p[3]}\n🔗 <b>Link:</b> {p[4]}", reply_markup=m)
    elif action.startswith("adm_link_"):
        plan_id = action.split("_")[2]
        msg = bot.send_message(call.message.chat.id, "🔗 Provide access delivery link URL for successful buyers:")
        bot.register_next_step_handler(msg, save_plan_link, plan_id)
    elif action.startswith("adm_media_"):
        plan_id = action.split("_")[2]
        msg = bot.send_message(call.message.chat.id, "📷 Send an Image or Video asset:")
        bot.register_next_step_handler(msg, save_plan_media, plan_id)
    elif action.startswith("adm_del_"):
        plan_id = int(action.split("_")[2])
        db.delete_plan(plan_id)
        bot.send_message(call.message.chat.id, "🗑 Package plan deleted permanently.")
    elif action.startswith("adm_app_"):
        _, _, u_id, p_id = action.split("_")
        plan = db.get_plan(int(p_id))
        link = plan[4] if plan[4] else "No Link provisioned yet. Contact Admin."
        bot.send_message(int(u_id), f"✅ <b>Payment Approved!</b>\n\n🎉 Your premium plan <b>{plan[1]}</b> has been activated.\n🌐 <b>Delivery Link Access:</b> {link}")
        bot.edit_message_caption("✅ Request Approved Successfully.", call.message.chat.id, call.message.message_id, reply_markup=None)
    elif action.startswith("adm_rej_"):
        _, _, u_id, p_id = action.split("_")
        bot.send_message(int(u_id), "❌ <b>Payment Rejected!</b>\n\nYour transaction verification proof failed audit checks.")
        bot.edit_message_caption("❌ Request Rejected Successfully.", call.message.chat.id, call.message.message_id, reply_markup=None)

def save_start_image(message):
    if message.photo:
        db.set_setting('start_image', message.photo[-1].file_id)
        bot.reply_to(message, "✅ Start banner welcome graphic saved successfully.")
    else:
        bot.reply_to(message, "❌ Aborted. Input received was not a regular photo asset.")

def save_welcome_text(message):
    if message.text:
        db.set_setting('welcome_text', message.text)
        bot.reply_to(message, "✅ Welcome landing content configured successfully.")
    else:
        bot.reply_to(message, "❌ Aborted. Missing plaintext configurations.")

def save_qr_code(message):
    if message.photo:
        db.set_setting('qr_code', message.photo[-1].file_id)
        bot.reply_to(message, "✅ Checkout QR Code image asset processed successfully.")
    else:
        bot.reply_to(message, "❌ Aborted. Please upload image files.")

def save_upi_id(message):
    if message.text:
        db.set_setting('upi_id', message.text)
        bot.reply_to(message, "✅ Target system routing UPI identifier active.")
    else:
        bot.reply_to(message, "❌ Aborted. Text string expected.")

def process_plan_name(message):
    if message.text:
        admin_states[message.chat.id] = {'name': message.text}
        msg = bot.send_message(message.chat.id, "💰 Enter Plan Price (numerical string only):")
        bot.register_next_step_handler(msg, process_plan_price)

def process_plan_price(message):
    if message.text:
        admin_states[message.chat.id]['price'] = message.text
        msg = bot.send_message(message.chat.id, "⏳ Enter Plan Validity period text (e.g. 30 Days):")
        bot.register_next_step_handler(msg, process_plan_validity)

def process_plan_validity(message):
    if message.text:
        state = admin_states.get(message.chat.id)
        if state:
            db.add_plan(state['name'], state['price'], message.text)
            bot.send_message(message.chat.id, "✅ Plan Set Successfully")
            admin_states.pop(message.chat.id, None)

def save_plan_link(message, plan_id):
    if message.text:
        db.update_plan_link(int(plan_id), message.text)
        bot.reply_to(message, "✅ Access URL linked to plan allocation mapping storage record data.")

def save_plan_media(message, plan_id):
    if message.photo:
        db.add_plan_media(int(plan_id), message.photo[-1].file_id, 'photo')
        bot.reply_to(message, "✅ Photo assets mapped directly inside plan package arrays.")
    elif message.video:
        db.add_plan_media(int(plan_id), message.video.file_id, 'video')
        bot.reply_to(message, "✅ Video file metadata successfully pinned inside plan configurations arrays.")
    else:
        bot.reply_to(message, "❌ Discarded.")

if __name__ == '__main__':
    db.init_db()
    logger.info("🤖 Bot core pipeline running directly via static files architecture.")
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20)
        except Exception as e:
            logger.error(f"⚠️ Re-establishing connection layer on break: {e}")
            time.sleep(5)
