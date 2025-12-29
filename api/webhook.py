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

THANK_YOU_TEXT = "ขอบคุณที่ซัพพอร์ต ฝากพิมพ์ +1 และ รีวิวในกลุ่ม VVIP ด้วยนะครับ"

# =========================================================
# [ส่วนตั้งค่าห้องให้เลือก] ใส่หลายห้องในราคาเดียวได้เลยครับ
# ลูกค้าจะเห็นปุ่มให้เลือกตามรายชื่อนี้
# =========================================================
ROOM_OPTIONS = {
    "200": [
        {"id": -1003465527678, "name": "VVIP V1 (หลัก)"},
        {"id": -1003465527678, "name": "VVIP V1 (สำรอง)"} # ตัวอย่าง: ใส่ ID ห้องอื่นได้
    ],
    "400": [
        {"id": -1003477489997, "name": "VVIP V1 SAVE"}
    ],
    "999": [
        {"id": -1003465527678, "name": "All Access V1"},
        {"id": -1003477489997, "name": "All Access V2"}
    ]
}

# เตรียมบอท
application = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ข้อความต้อนรับเดิม
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
# ฟังก์ชันจัดการ: รูปภาพสลิป (ลูกค้าส่งมา)
# ---------------------------------------------------------
async def handle_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    name = user.first_name
    
    await update.message.reply_text("⏳ ได้รับสลิปแล้วครับ รอแอดมินตรวจสอบสักครู่นะครับ...")
    
    # ปุ่มกดสำหรับแอดมิน (admin_approve_ราคา_ไอดีลูกค้า)
    keyboard = [
        [
            InlineKeyboardButton("✅ 200", callback_data=f"admin_approve_200_{user_id}"),
            InlineKeyboardButton("✅ 400", callback_data=f"admin_approve_400_{user_id}")
        ],
        [
            InlineKeyboardButton("✅ 999 (ถาวร)", callback_data=f"admin_approve_999_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    caption_text = f"📩 **สลิปใหม่ (โอนธนาคาร)**\nชื่อ: {name}\nID: {user_id}\n\nตรวจสอบยอดแล้วกดปุ่ม:"
    
    try:
        await context.bot.send_photo(chat_id=ADMIN_GROUP_ID, photo=update.message.photo[-1].file_id, caption=caption_text, reply_markup=reply_markup)
    except Exception as e:
        print(f"Error sending to admin: {e}")

# ---------------------------------------------------------
# ฟังก์ชันจัดการ: ลิ้งก์ซอง TrueMoney
# ---------------------------------------------------------
async def handle_truemoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.message.from_user
    user_id = user.id
    name = user.first_name

    await update.message.reply_text("🧧 ได้รับลิ้งก์ซองแล้วครับ! แอดมินกำลังกดรับและตรวจสอบยอด สักครู่นะครับ...")

    keyboard = [
        [
            InlineKeyboardButton("✅ 200", callback_data=f"admin_approve_200_{user_id}"),
            InlineKeyboardButton("✅ 400", callback_data=f"admin_approve_400_{user_id}")
        ],
        [
            InlineKeyboardButton("✅ 999 (ถาวร)", callback_data=f"admin_approve_999_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    admin_text = f"🧧 **มีซอง TrueMoney เข้าใหม่!**\n\nจากลูกค้า: {name}\nลิ้งก์: {text}\n\n👉 **กดที่ลิ้งก์เพื่อรับเงิน** แล้วกลับมากดปุ่มอนุมัติด้านล่างครับ:"

    try:
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_text, reply_markup=reply_markup)
    except Exception as e:
        print(f"Error sending link to admin: {e}")


# ===========================================================
# ส่วนจัดการปุ่มกด (ทั้งของ Admin และ ลูกค้า)
# ===========================================================
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # ตอบรับการกดปุ่มเพื่อไม่ให้โหลดค้าง
    
    data = query.data

    # -------------------------------------------------
    # กรณี 1: Admin กดอนุมัติ (ขึ้นต้นด้วย admin_approve)
    # -------------------------------------------------
    if data.startswith("admin_approve_"):
        try:
            _, _, price, customer_id = data.split('_')
            customer_id = int(customer_id)
            
            # ดึงรายชื่อห้องตามราคา
            rooms = ROOM_OPTIONS.get(price, [])
            
            if not rooms:
                await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"❌ ไม่พบข้อมูลห้องสำหรับราคา {price}")
                return

            # สร้างปุ่มให้ลูกค้าเลือก (ส่งไปหาลูกค้า)
            customer_keyboard = []
            for room in rooms:
                # callback data รูปแบบ: select_room_{IDห้อง}_{ราคา}
                btn_text = f"เข้าห้อง {room['name']}"
                callback_str = f"select_room_{room['id']}_{price}"
                customer_keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_str)])
            
            cust_markup = InlineKeyboardMarkup(customer_keyboard)
            
            # ส่งข้อความหาลูกค้า
            await context.bot.send_message(
                chat_id=customer_id,
                text=f"✅ **ยอด {price} บาท ได้รับการอนุมัติแล้ว**\n\nกรุณาเลือกห้องที่ต้องการเข้า (เลือกได้ 1 ห้องเท่านั้น):",
                reply_markup=cust_markup
            )
            
            # แก้ไขข้อความแอดมินให้รู้ว่ากดไปแล้ว
            if query.message.caption:
                await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ อนุมัติยอด {price} แล้ว (รอเกสเลือกห้อง)")
            else:
                await query.edit_message_text(text=f"{query.message.text}\n\n✅ อนุมัติยอด {price} แล้ว (รอเกสเลือกห้อง)")
                
        except Exception as e:
            print(f"Admin Error: {e}")

    # -------------------------------------------------
    # กรณี 2: ลูกค้ากดเลือกห้อง (ขึ้นต้นด้วย select_room)
    # -------------------------------------------------
    elif data.startswith("select_room_"):
        # Logic: สร้างลิ้งก์ -> ส่งให้ -> ลบปุ่มทิ้งทันที
        try:
            parts = data.split('_')
            target_group_id = int(parts[2]) # ID ห้อง
            price_label = parts[3]          # ราคา (เอาไว้ตั้งชื่อลิ้งก์)

            # 1. สร้างลิ้งก์เข้ากลุ่ม
            invite_link_obj = await context.bot.create_chat_invite_link(
                chat_id=target_group_id, 
                member_limit=1, 
                name=f"VVIP {price_label} Selected"
            )
            
            # 2. เตรียมปุ่มลิ้งก์ (แบบกดแล้วไปเลย ไม่ใช่ Callback)
            link_keyboard = [[InlineKeyboardButton("⭐️ กดเข้ากลุ่มที่นี่ ⭐️", url=invite_link_obj.invite_link)]]
            link_markup = InlineKeyboardMarkup(link_keyboard)
            
            # 3. [สำคัญมาก] แก้ไขข้อความเดิม ลบปุ่มตัวเลือกทิ้ง แทนที่ด้วยลิ้งก์
            # นี่คือเทคนิคที่ทำให้ลูกค้าเลือกได้แค่ห้องเดียว ย้อนกลับไม่ได้
            await query.edit_message_text(
                text=f"✅ **ยืนยันการเลือกห้องเรียบร้อย**\n\nนี่คือลิ้งก์สำหรับเข้าห้องของคุณครับ:\n(ลิ้งก์ใช้ได้ครั้งเดียว)",
                reply_markup=link_markup
            )
            
            # ส่งข้อความขอบคุณตามหลัง
            await context.bot.send_message(chat_id=query.from_user.id, text=THANK_YOU_TEXT)

        except Exception as e:
            print(f"Customer Error: {e}")
            await context.bot.send_message(
                chat_id=query.from_user.id, 
                text="❌ เกิดข้อผิดพลาดในการสร้างลิ้งก์ (บอทอาจไม่ได้เป็นแอดมินในกลุ่มนั้น) โปรดแจ้งแอดมิน"
            )


# ===========================================================
# ส่วนลงทะเบียน Handler
# ===========================================================

application.add_handler(CommandHandler('start', start))
application.add_handler(MessageHandler(filters.PHOTO, handle_slip))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("gift.truemoney.com"), handle_truemoney))
application.add_handler(CallbackQueryHandler(button_click))

# ===========================================================
# ส่วน Server สำหรับ Vercel (คงเดิม)
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
