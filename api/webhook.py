import os
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler

# =================ตั้งค่าข้อมูลระบบ=================
TOKEN = os.environ.get("TELEGRAM_TOKEN") 
ADMIN_GROUP_ID = -5101530019
QR_IMAGE_URL = 'https://img2.pic.in.th/photo_2025-12-29_21-12-44.jpg'

# ---------------------------------------------------------
# [สำคัญ] เอาเลข ID กลุ่ม (ที่ขึ้นต้นด้วย -100) มาใส่ตรงนี้ครับ
# ---------------------------------------------------------
GROUP_ID_200_V1 = -1003465527678   # กลุ่ม 200
GROUP_ID_400 = -1003477489997   # กลุ่ม 400
GROUP_ID_999 = -1003465527678   # กลุ่ม VIP
# GROUP_ID_200V2 = -1003592949127 # กลุ่มน้องใหม่

THANK_YOU_TEXT = "ขอบคุณที่ซัพพอร์ต ฝากพิมพ์ +1 และ รีวิวในกลุ่ม VVIP ด้วยนะครับ"
# ===============================================

WELCOME_TEXT = """
กลุ่ม VVIP By.เซียนจู

ค่าเข้า 200 บาท ( เซฟไม่ได้)
400 บาท ( เซฟได้ )
999 ถาวรเข้าได้ทุกกลุ่ม

ตัวอย่างกลุ่มVVIP
https://t.me/+5sWrRGBIm3Y5ODE1

เช็คเครดิตได้ที่
https://t.me/+uoEnKbH_PP05NWQ1
"""

# เตรียมบอท
application = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=WELCOME_TEXT)
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id, 
            photo=QR_IMAGE_URL,
            caption="📸 **ชำระเงินได้ 2 ช่องทาง**\n\n1. สแกน QR Code แล้วส่งสลิป\n2. หรือ ส่งลิ้งก์ซองของขวัญ (TrueMoney) มาในแชทนี้ได้เลยครับ"
        )
    except Exception as e:
        print(f"Error sending photo: {e}")

# ---------------------------------------------------------
# ฟังก์ชันจัดการ: รูปภาพสลิป
# ---------------------------------------------------------
async def handle_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    name = user.first_name
    
    await update.message.reply_text("⏳ ได้รับสลิปแล้วครับ รอแอดมินตรวจสอบสักครู่นะครับ...")
    
    # สร้างปุ่มสำหรับแอดมิน
    keyboard = [
        [
            InlineKeyboardButton("✅ 200", callback_data=f"ap_200_{user_id}"),
            InlineKeyboardButton("✅ 400", callback_data=f"ap_400_{user_id}")
        ],
        [
            InlineKeyboardButton("✅ 999 (ถาวร)", callback_data=f"ap_999_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    caption_text = f"📩 **สลิปใหม่ (โอนธนาคาร)**\nชื่อ: {name}\nID: {user_id}\n\nตรวจสอบยอดแล้วกดปุ่ม:"
    
    try:
        await context.bot.send_photo(chat_id=ADMIN_GROUP_ID, photo=update.message.photo[-1].file_id, caption=caption_text, reply_markup=reply_markup)
    except Exception as e:
        print(f"Error sending to admin: {e}")

# ---------------------------------------------------------
# [ใหม่] ฟังก์ชันจัดการ: ลิ้งก์ซอง TrueMoney
# ---------------------------------------------------------
async def handle_truemoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user
    user_id = user.id
    name = user.first_name

    # ตอบกลับลูกค้า
    await update.message.reply_text("🧧 ได้รับลิ้งก์ซองแล้วครับ! แอดมินกำลังกดรับและตรวจสอบยอด สักครู่นะครับ...")

    # สร้างปุ่มสำหรับแอดมิน
    keyboard = [
        [
            InlineKeyboardButton("✅ 200", callback_data=f"ap_200_{user_id}"),
            InlineKeyboardButton("✅ 400", callback_data=f"ap_400_{user_id}")
        ],
        [
            InlineKeyboardButton("✅ 999 (ถาวร)", callback_data=f"ap_999_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ส่งข้อความให้แอดมินกดรับซอง
    admin_text = f"🧧 **มีซอง TrueMoney เข้าใหม่!**\n\nจากลูกค้า: {name}\nลิ้งก์: {text}\n\n👉 **กดที่ลิ้งก์เพื่อรับเงิน** แล้วกลับมากดปุ่มอนุมัติด้านล่างครับ:"

    try:
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_text, reply_markup=reply_markup)
    except Exception as e:
        print(f"Error sending link to admin: {e}")


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data.split('_')
    price = data[1]
    customer_id = int(data[2])

    target_groups = [] 

    if price == "200":
        target_groups.append({"id": GROUP_ID_200, "name": "ห้อง 200"}) 
        
    elif price == "400":
        target_groups.append({"id": GROUP_ID_400, "name": "ห้อง 400"})
        
    else: # กรณี 999
        target_groups.append({"id": GROUP_ID_200_V1, "name": "ห้อง VVIP V1"})
        # target_groups.append({"id": GROUP_ID_400, "name": "ห้อง VVIP V1 SAVE"})
        # target_groups.append({"id": GROUP_ID_999, "name": "ห้อง VIP"})
        # target_groups.append({"id": GROUP_ID_200V2, "name": "ห้องน้องใหม่"}) 
        

    try:
        keyboard = []
        for group in target_groups:
            invite_link_obj = await context.bot.create_chat_invite_link(
                chat_id=group["id"], 
                member_limit=1, 
                name=f"VVIP {price} Slip {customer_id}"
            )
            btn_text = f"⭐️ กดเข้า {group['name']}"
            keyboard.append([InlineKeyboardButton(btn_text, url=invite_link_obj.invite_link)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        final_message = f"✅ ยอด {price} บาท อนุมัติเรียบร้อยครับ\n\n👇 กดปุ่มด้านล่างเพื่อเข้ากลุ่มได้เลยครับ\n(แยกลิ้งก์ตามกลุ่ม กดเข้าให้ครบนะครับ)\n\n{THANK_YOU_TEXT}"

        await context.bot.send_message(
            chat_id=customer_id, 
            text=final_message, 
            reply_markup=reply_markup,
            protect_content=True
        )
        
        # แก้ไขข้อความในห้องแอดมิน
        if query.message.caption: # กรณีเป็นรูปภาพ
             await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ อนุมัติยอด {price} เรียบร้อย")
        else: # กรณีเป็นข้อความ (ซองทรู)
             await query.edit_message_text(text=f"{query.message.text}\n\n✅ อนุมัติยอด {price} เรียบร้อย")

    except Exception as e:
        print(f"Error generating link or replying: {e}")
        error_text = f"❌ เกิดข้อผิดพลาด: บอทอาจยังไม่ได้เป็น Admin ในกลุ่มเป้าหมาย หรือเลขกลุ่มผิด ({e})"
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=error_text)


# ===========================================================
# ส่วนลงทะเบียน Handler
# ===========================================================

application.add_handler(CommandHandler('start', start))

# รับรูปภาพ (สลิป)
application.add_handler(MessageHandler(filters.PHOTO, handle_slip))

# รับข้อความที่มีคำว่า gift.truemoney.com (ซอง)
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("gift.truemoney.com"), handle_truemoney))

# จัดการปุ่มกด
application.add_handler(CallbackQueryHandler(button_click))

# ===========================================================
# ส่วน Server สำหรับ Vercel
# ===========================================================
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
