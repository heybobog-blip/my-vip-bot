import os
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# =================ตั้งค่าข้อมูลระบบ (ดึงจาก Vercel Environment)=================
# เราจะไปตั้งค่า TOKEN ในหน้าเว็บ Vercel เพื่อความปลอดภัย
TOKEN = os.environ.get("TELEGRAM_TOKEN") 
ADMIN_GROUP_ID = -5101530019
QR_IMAGE_URL = 'https://img2.pic.in.th/photo_2025-12-29_21-12-44.jpg'

LINK_200 = "https://t.me/+m2H5MlD_04c2N2M1"
LINK_400 = "https://t.me/+6tEwQkfNvfc4ZTBl"
LINK_999 = "https://t.me/+m2H5MlD_04c2N2M1"

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

# เตรียมบอท (Initialize Application)
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
    await query.answer()

    data = query.data.split('_')
    price = data[1]
    customer_id = int(data[2])

    # เลือกลิ้งค์ตามราคา
    invite_link = LINK_200 if price == "200" else (LINK_400 if price == "400" else LINK_999)
    
    # --- ส่วนที่แก้ใหม่: เปลี่ยนลิ้งค์เป็นปุ่ม และป้องกันการก๊อป ---
    
    # 1. สร้างปุ่มลิ้งค์ (ลูกค้ากดปุ่มนี้จะเด้งไปเข้ากลุ่มเลย)
    keyboard = [
        [InlineKeyboardButton("🔗 แตะเพื่อเข้ากลุ่ม VVIP ทันที", url=invite_link)]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 2. ข้อความใหม่ (เอาลิ้งค์ดิบออก บอกให้กดปุ่มแทน)
    final_message = f"✅ ยอด {price} บาท อนุมัติเรียบร้อยครับ\n\n👇 กดปุ่มด้านล่างเพื่อเข้ากลุ่มได้เลยครับ\n\n{THANK_YOU_TEXT}"

    try:
        # 3. ส่งหาลูกค้าพร้อมปุ่ม + เปิดโหมด protect_content=True (ห้าม Save/Forward)
        await context.bot.send_message(
            chat_id=customer_id, 
            text=final_message, 
            reply_markup=reply_markup,
            protect_content=True 
        )
        
        # อัปเดตข้อความฝั่งแอดมินให้รู้ว่ากดไปแล้ว
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ อนุมัติยอด {price} เรียบร้อย")
    except Exception as e:
        print(f"Error replying to customer: {e}")
