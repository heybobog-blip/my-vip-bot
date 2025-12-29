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
# วิธีหา: เชิญ @RawDataBot เข้ากลุ่ม แล้วดู field "id"
# ---------------------------------------------------------
GROUP_ID_200 = -1003465527678  # ### แก้ตรงนี้: ใส่ ID กลุ่มราคา 200 ###
GROUP_ID_400 = -1003477489997  # ### แก้ตรงนี้: ใส่ ID กลุ่มราคา 400 ###
GROUP_ID_999 = -1003465527678  # ### แก้ตรงนี้: ใส่ ID กลุ่มราคา 999 ###

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
            caption="📸 สแกน QR Code เพื่อชำระเงิน\n\nโอนแล้ว **ส่งสลิป** เข้ามาในแชทนี้ได้เลยครับ แอดมินจะตรวจสอบสักครู่"
        )
    except Exception as e:
        print(f"Error sending photo: {e}")

async def handle_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    name = user.first_name
    
    await update.message.reply_text("⏳ ได้รับสลิปแล้วครับ รอแอดมินตรวจสอบและกดอนุมัติสักครู่นะครับ...")

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
    caption_text = f"📩 สลิปใหม่!\nชื่อ: {name}\nID: {user_id}\n\nตรวจสอบยอดแล้วกดปุ่ม:"
    
    try:
        await context.bot.send_photo(chat_id=ADMIN_GROUP_ID, photo=update.message.photo[-1].file_id, caption=caption_text, reply_markup=reply_markup)
    except Exception as e:
        print(f"Error sending to admin: {e}")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # ตอบกลับเพื่อให้ปุ่มหายโหลด

    data = query.data.split('_')
    price = data[1]
    customer_id = int(data[2])

    # 1. เลือก ID กลุ่มเป้าหมาย ตามราคาที่กด
    target_group_id = 0
    if price == "200":
        target_group_id = GROUP_ID_200
    elif price == "400":
        target_group_id = GROUP_ID_400
    else:
        target_group_id = GROUP_ID_999

    try:
        # 2. คำสั่งสร้างลิงก์แบบใช้ครั้งเดียว (member_limit=1)
        # บอทต้องเป็น Admin ในกลุ่มนั้นก่อน ถึงจะสร้างได้
        invite_link_obj = await context.bot.create_chat_invite_link(
            chat_id=target_group_id, 
            member_limit=1,  # เข้าได้ 1 คนเท่านั้น
            name=f"VVIP Slip {customer_id}" # (Optional) ตั้งชื่อลิงก์เพื่อให้แอดมินรู้ว่าใครใช้
        )
        
        # ดึง URL ออกมาจาก Object
        final_link = invite_link_obj.invite_link

        # --- ส่วนสร้างปุ่มลิ้งค์ ---
        keyboard = [
            [InlineKeyboardButton("🔗 แตะเพื่อเข้ากลุ่ม VVIP ทันที", url=final_link)]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        final_message = f"✅ ยอด {price} บาท อนุมัติเรียบร้อยครับ\n\n👇 กดปุ่มด้านล่างเพื่อเข้ากลุ่มได้เลยครับ\n(ลิงก์นี้เข้าได้แค่ครั้งเดียว ห้ามส่งต่อ)\n\n{THANK_YOU_TEXT}"

        # ส่งข้อความหาลูกค้า
        await context.bot.send_message(
            chat_id=customer_id, 
            text=final_message, 
            reply_markup=reply_markup,
            protect_content=True
        )
        
        # แก้ไขข้อความในห้องแอดมินว่า อนุมัติแล้ว
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ อนุมัติยอด {price} เรียบร้อย\n(สร้างลิงก์ใช้ครั้งเดียวสำเร็จ)")

    except Exception as e:
        # กรณีเกิด Error (เช่น ลืมดึงบอทเข้ากลุ่ม หรือ ใส่เลขกลุ่มผิด)
        print(f"Error generating link or replying: {e}")
        error_text = f"❌ เกิดข้อผิดพลาด: บอทอาจยังไม่ได้เป็น Admin ในกลุ่มเป้าหมาย หรือเลขกลุ่มผิด ({e})"
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=error_text)


# ลงทะเบียน Handler
application.add_handler(CommandHandler('start', start))
application.add_handler(MessageHandler(filters.PHOTO, handle_slip))
application.add_handler(CallbackQueryHandler(button_click))

# ฟังก์ชันสำหรับ Vercel
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
