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
# ฟังก์ชันแกะซอง TrueMoney (ทำงานเบื้องหลัง)
# =========================================================
def redeem_truemoney(url, phone_number):
    try:
        # ดึงรหัส Voucher จาก URL
        match = re.search(r'v=([a-zA-Z0-9]+)', url)
        if not match:
            return {"status": "error", "message": "ลิ้งก์ไม่ถูกต้อง"}
        
        voucher_code = match.group(1)
        
        # ส่ง Request ไปหา TrueMoney
        headers = {'content-type': 'application/json'}
        payload = {
            "mobile": phone_number,
            "voucher_hash": voucher_code
        }
        
        response = requests.post(
            f"https://gift.truemoney.com/campaign/vouchers/{voucher_code}/redeem", 
            json=payload, 
            headers=headers,
            timeout=10
        )
        
        data = response.json()
        
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
            return {"status": "error", "message": "เกิดข้อผิดพลาด หรือ ลิ้งก์หมดอายุ"}

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
    # ปุ่มติดต่อ Admin
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

# ---------------------------------------------------------
# ฟังก์ชัน: แจ้งเตือนเมื่อลูกค้าส่งรูป/สลิป (ปฏิเสธ)
# ---------------------------------------------------------
async def reject_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    warning_text = """
❌ **ระบบไม่รับสลิปธนาคาร หรือ QR Code ครับ**

⚠️ กรุณาส่งเป็น **"ลิ้งก์ซองของขวัญ TrueMoney"** เท่านั้น
เพื่อให้ระบบตรวจสอบและดึงเข้ากลุ่มอัตโนมัติครับ
"""
    await update.message.reply_text(warning_text)

# ---------------------------------------------------------
# ฟังก์ชัน: รับลิ้งก์ซอง TrueMoney และทำงานอัตโนมัติ
# ---------------------------------------------------------
async def handle_truemoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name

    await update.message.reply_text("🤖 บอทได้รับลิ้งก์แล้ว กำลังตรวจสอบและรับเงินอัตโนมัติ รอสักครู่ครับ...")

    # เรียกใช้ฟังก์ชันรับเงิน
    # หมายเหตุ: การใช้ requests ใน async อาจหน่วงนิดหน่อย แต่ถ้ายอดไม่เยอะใช้ได้ครับ
    try:
        result = redeem_truemoney(link, MY_PHONE_NUMBER)
    except Exception as e:
        result = {"status": "error", "message": f"System Error: {e}"}

    # -----------------------------------------------------
    # กรณีรับเงินสำเร็จ
    # -----------------------------------------------------
    if result['status'] == 'success':
        amount = result['amount'] # ยอดเงินที่ได้รับ (Integer)
        sender = result['sender']
        
        # 1. แจ้งแอดมินว่าบอทรับเงินแล้ว
        admin_report = f"💰 **บอทรับเงินสำเร็จ!**\n\nจาก: {user_name} (ID: {user_id})\nยอดเงิน: {amount} บาท\nชื่อในซอง: {sender}\n\n✅ ระบบกำลังส่งลิ้งก์ให้ลูกค้า..."
        try:
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_report)
        except:
            pass # ถ้าส่งหาแอดมินไม่ได้ ก็ปล่อยผ่านไปทำงานต่อ

        # 2. Logic การส่งห้องตามยอดเงิน (Auto Approve)
        
        # >>>> กรณี 999 (เหมา) <<<<
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

        # >>>> กรณี 200 หรือ 400 (เลือกห้อง) <<<<
        elif str(amount) in SELECTABLE_ROOMS: # เช็คว่ายอดตรงกับคีย์ "200" หรือ "400" ไหม
            rooms = SELECTABLE_ROOMS[str(amount)]
            customer_keyboard = []
            for room in rooms:
                # สร้างปุ่มให้เลือก
                callback_str = f"select_room_{room['id']}_{amount}"
                customer_keyboard.append([InlineKeyboardButton(f"เลือกเข้า {room['name']}", callback_data=callback_str)])
            
            cust_markup = InlineKeyboardMarkup(customer_keyboard)
            await update.message.reply_text(
                f"✅ **ได้รับยอด {amount} บาท เรียบร้อย**\n👇 กรุณากดเลือกห้องที่ต้องการเข้า (เลือกได้ 1 ห้องเท่านั้น):",
                reply_markup=cust_markup
            )
        
        # >>>> กรณียอดไม่ตรงเงื่อนไข <<<<
        else:
            await update.message.reply_text(
                f"✅ ได้รับยอด {amount} บาท (แต่ไม่ตรงกับแพ็กเกจปกติ)\nกรุณาแคปหน้าจอนี้แจ้งแอดมินเพื่อตรวจสอบครับ"
            )
            # เพิ่มปุ่มติดต่อแอดมินให้
            contact_kb = [
                [InlineKeyboardButton("💬 ติดต่อ Admin", url="https://t.me/ZeinJu001")]
            ]
            await update.message.reply_text("หรือกดปุ่มเพื่อติดต่อแอดมิน:", reply_markup=InlineKeyboardMarkup(contact_kb))

    # -----------------------------------------------------
    # กรณีรับเงินไม่สำเร็จ (เช่น ซองหมด, ลิ้งก์ผิด)
    # -----------------------------------------------------
    else:
        error_msg = result['message']
        await update.message.reply_text(f"❌ **ทำรายการไม่สำเร็จ**\n\nสาเหตุ: {error_msg}\n\nหากมั่นใจว่าลิ้งก์ถูก โปรดติดต่อแอดมินครับ")


# ---------------------------------------------------------
# ฟังก์ชันจัดการปุ่มกด (สำหรับคนที่เลือกห้อง 200/400)
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

            # สร้างลิ้งก์เข้ากลุ่ม
            invite_link_obj = await context.bot.create_chat_invite_link(
                chat_id=target_group_id, 
                member_limit=1, 
                name=f"Auto Select {price_label}"
            )
            
            # ปุ่มลิ้งก์
            link_keyboard = [[InlineKeyboardButton("⭐️ กดเข้ากลุ่มที่นี่ ⭐️", url=invite_link_obj.invite_link)]]
            link_markup = InlineKeyboardMarkup(link_keyboard)
            
            # ลบปุ่มเลือกทิ้ง แทนที่ด้วยลิ้งก์
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

# ดักจับลิงค์ซอง TrueMoney (gift.truemoney.com)
application.add_handler(MessageHandler(filters.Regex("gift.truemoney.com"), handle_truemoney))

# ดักจับรูปภาพ (เพื่อแจ้งเตือนว่าไม่รับ)
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
