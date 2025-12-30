import os
import json
import asyncio
import re
import requests  # จำเป็นต้องมี module นี้
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler

# =================ตั้งค่าข้อมูลระบบ=================
TOKEN = os.environ.get("TELEGRAM_TOKEN")

# เลขห้องแอดมิน (สำหรับส่งรายงานว่าบอทรับเงินแล้ว)
ADMIN_GROUP_ID = -1003614142313

# เบอร์สำหรับรับเงิน (บอทจะกรอกเบอร์นี้เอง)
MY_PHONE_NUMBER = "0659325591" 

# =========================================================
# [ตั้งค่าห้องลูกค้า]
# =========================================================
SELECTABLE_ROOMS = {
    "200": [
        {"id": -1003465527678, "name": "VVIP V1"},
        {"id": -1003465527678, "name": "VVIP V2"},
    ],
    "400": [
        {"id": -1003477489997, "name": "VVIP V1 SAVE"}
    ]
}

ALL_ACCESS_ROOMS = [
    {"id": -1003477489997, "name": "VVIP V1 SAVE"},
    # {"id": -1003465527678, "name": "VVIP V1"}, 
]

# ข้อความขอบคุณ
THANK_YOU_TEXT = "ขอบคุณที่ซัพพอร์ต ฝากพิมพ์ +1 และ รีวิวในกลุ่ม VVIP ด้วยนะครับ"

# เตรียมบอท
application = ApplicationBuilder().token(TOKEN).build()

# =========================================================
# ฟังก์ชันแกะซอง TrueMoney (ฉบับแก้ไข: เพิ่ม User-Agent หลอก server)
# =========================================================
def redeem_truemoney(url, phone_number):
    try:
        # ดึงรหัส Voucher จาก URL
        match = re.search(r'v=([a-zA-Z0-9]+)', url)
        if not match:
            return {"status": "error", "message": "รูปแบบลิ้งก์ไม่ถูกต้อง"}
        
        voucher_code = match.group(1)
        
        # [แก้จุดที่ 1] เพิ่ม User-Agent ให้เหมือน Chrome Browser
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Origin': 'https://gift.truemoney.com',
            'Referer': 'https://gift.truemoney.com/'
        }
        
        payload = {
            "mobile": phone_number,
            "voucher_hash": voucher_code
        }
        
        response = requests.post(
            f"https://gift.truemoney.com/campaign/vouchers/{voucher_code}/redeem", 
            json=payload, 
            headers=headers,
            timeout=15
        )
        
        # [แก้จุดที่ 2] เช็คก่อนว่า TrueMoney ตอบกลับมาเป็น JSON หรือไม่
        if response.status_code != 200:
             return {"status": "error", "message": f"Server ปฏิเสธการเชื่อมต่อ (Code: {response.status_code}) อาจเป็นเพราะ IP ต่างประเทศ"}

        try:
            data = response.json()
        except json.JSONDecodeError:
            return {"status": "error", "message": "อ่านค่าจาก TrueMoney ไม่ได้ (Response ไม่ใช่ JSON)"}
        
        if data['status']['code'] == 'SUCCESS':
            amount = float(data['data']['my_ticket']['amount_baht'])
            sender_name = data['data']['owner_profile']['nickname']
            return {"status": "success", "amount": int(amount), "sender": sender_name}
        
        elif data['status']['code'] == 'CANNOT_GET_OWN_VOUCHER':
            return {"status": "error", "message": "ไม่สามารถรับซองของตัวเองได้"}
        elif data['status']['code'] == 'TARGET_USER_REDEEMED':
             return {"status": "error", "message": "ซองนี้ถูกรับไปแล้ว"}
        elif data['status']['code'] == 'VOUCHER_OUT_OF_STOCK':
             return {"status": "error", "message": "ซองนี้หมดแล้ว"}
        else:
            return {"status": "error", "message": f"รับเงินไม่ได้: {data['status']['code']}"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

# =========================================================
# ส่วนของ Bot Handlers
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    WELCOME_TEXT = """
🧧 **ระบบรับเฉพาะ "ซองของขวัญ TrueMoney" เท่านั้น** 🧧
❌ ไม่รับโอนธนาคาร / ไม่รับสแกน QR Code

👇 **เรทราคาค่าเข้า**
✅ **200 บาท** : ดูในกลุ่ม (เซฟไม่ได้)
✅ **400 บาท** : ดู + เซฟลงเครื่องได้ 💾
🏆 **999 บาท** : เหมาถาวร เข้าได้ทุกกลุ่ม!

🤖 **ระบบอัตโนมัติ 24 ชม.**
เพียงส่ง "ลิ้งก์ซองของขวัญ" มาในแชทนี้
บอทจะตรวจสอบยอดและส่งทางเข้าให้ทันที!
"""
    keyboard = [
        [InlineKeyboardButton("💬 ติดต่อ Admin (1)", url="https://t.me/ZeinJu001")],
        [InlineKeyboardButton("💬 ติดต่อ Admin (2)", url="https://t.me/duded16")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=WELCOME_TEXT, 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def reject_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    warning_text = """
❌ **ระบบไม่รับสลิปธนาคาร หรือ QR Code ครับ**

⚠️ กรุณาส่งเป็น **"ลิ้งก์ซองของขวัญ TrueMoney"** เท่านั้น
เพื่อให้ระบบตรวจสอบและดึงเข้ากลุ่มอัตโนมัติครับ
"""
    await update.message.reply_text(warning_text)

async def handle_truemoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name

    await update.message.reply_text("🤖 บอทได้รับลิ้งก์แล้ว กำลังตรวจสอบและรับเงินอัตโนมัติ รอสักครู่ครับ...")

    # เรียกใช้ฟังก์ชันรับเงิน
    result = await asyncio.to_thread(redeem_truemoney, link, MY_PHONE_NUMBER)

    # -----------------------------------------------------
    # กรณีรับเงินสำเร็จ
    # -----------------------------------------------------
    if result['status'] == 'success':
        amount = result['amount'] 
        sender = result['sender']
        
        # แจ้งแอดมิน
        admin_report = f"💰 **บอทรับเงินสำเร็จ!**\n\nจาก: {user_name} (ID: {user_id})\nยอดเงิน: {amount} บาท\nชื่อในซอง: {sender}\n\n✅ ระบบกำลังส่งลิ้งก์ให้ลูกค้า..."
        try:
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_report)
        except:
            pass 

        # Auto Approve
        if amount >= 999:
            links_keyboard = []
            for group in ALL_ACCESS_ROOMS:
                invite = await context.bot.create_chat_invite_link(
                    chat_id=group["id"], member_limit=1, name=f"Auto 999 {user_id}"
                )
                links_keyboard.append([InlineKeyboardButton(f"เข้า {group['name']}", url=invite.invite_link)])
            
            final_markup = InlineKeyboardMarkup(links_keyboard)
            await update.message.reply_text(
                f"✅ **ได้รับยอด {amount} บาท เรียบร้อย**\n🎉 ยินดีด้วยครับ คุณได้รับสิทธิ์ VIP ถาวร (เข้าครบทุกห้อง)\n\nกดปุ่มด้านล่างเพื่อเข้าห้องได้เลยครับ:",
                reply_markup=final_markup
            )

        elif str(amount) in SELECTABLE_ROOMS:
            rooms = SELECTABLE_ROOMS[str(amount)]
            customer_keyboard = []
            for room in rooms:
                callback_str = f"select_room_{room['id']}_{amount}"
                customer_keyboard.append([InlineKeyboardButton(f"เลือกเข้า {room['name']}", callback_data=callback_str)])
            
            cust_markup = InlineKeyboardMarkup(customer_keyboard)
            await update.message.reply_text(
                f"✅ **ได้รับยอด {amount} บาท เรียบร้อย**\n👇 กรุณากดเลือกห้องที่ต้องการเข้า (เลือกได้ 1 ห้องเท่านั้น):",
                reply_markup=cust_markup
            )
        
        else:
            await update.message.reply_text(
                f"✅ ได้รับยอด {amount} บาท (แต่ไม่ตรงกับแพ็กเกจปกติ)\nกรุณาแคปหน้าจอนี้แจ้งแอดมินเพื่อตรวจสอบครับ"
            )
            contact_kb = [[InlineKeyboardButton("💬 ติดต่อ Admin", url="https://t.me/ZeinJu001")]]
            await update.message.reply_text("หรือกดปุ่มเพื่อติดต่อแอดมิน:", reply_markup=InlineKeyboardMarkup(contact_kb))

    # -----------------------------------------------------
    # กรณีรับเงินไม่สำเร็จ
    # -----------------------------------------------------
    else:
        error_msg = result['message']
        contact_kb = [[InlineKeyboardButton("💬 แจ้งแอดมิน", url="https://t.me/ZeinJu001")]]
        
        # แจ้งลูกค้า
        await update.message.reply_text(
            f"❌ **ทำรายการไม่สำเร็จ**\n\nสาเหตุ: {error_msg}\n\nหากมั่นใจว่าลิ้งก์ถูกต้อง ให้กดปุ่มด้านล่างเพื่อแจ้งแอดมินครับ",
            reply_markup=InlineKeyboardMarkup(contact_kb)
        )

# ---------------------------------------------------------
# ฟังก์ชันจัดการปุ่มกด
# ---------------------------------------------------------
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data

    if data.startswith("select_room_"):
        try:
            parts = data.split('_')
            target_group_id = int(parts[2])
            price_label = parts[3]

            invite_link_obj = await context.bot.create_chat_invite_link(
                chat_id=target_group_id, member_limit=1, name=f"Auto Select {price_label}"
            )
            
            link_keyboard = [[InlineKeyboardButton("⭐️ กดเข้ากลุ่มที่นี่ ⭐️", url=invite_link_obj.invite_link)]]
            link_markup = InlineKeyboardMarkup(link_keyboard)
            
            await query.edit_message_text(
                text=f"✅ **เลือกห้องเรียบร้อย**\n\nกดปุ่มด้านล่างเพื่อเข้าห้องได้เลยครับ:\n(ลิ้งก์ใช้ได้ครั้งเดียว)",
                reply_markup=link_markup
            )
            
            await context.bot.send_message(chat_id=query.from_user.id, text=THANK_YOU_TEXT)

        except Exception as e:
            await context.bot.send_message(chat_id=query.from_user.id, text="❌ เกิดข้อผิดพลาดในการสร้างลิ้งก์ โปรดติดต่อแอดมิน")

# ===========================================================
# Server
# ===========================================================
application.add_handler(CommandHandler('start', start))
application.add_handler(MessageHandler(filters.Regex("gift.truemoney.com"), handle_truemoney))
application.add_handler(MessageHandler(filters.PHOTO, reject_slip))
application.add_handler(CallbackQueryHandler(button_click))

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        json_string = post_body.decode('utf-8')
        
        update_data = json.loads(json_string)
        
        async def main():
            async with application:
                update = Update.de_json(update_data, application.bot)
                await application.process_update(update)

        try:
            asyncio.run(main())
        except RuntimeError:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
