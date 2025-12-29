import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# =================ตั้งค่าข้อมูลระบบ=================
TOKEN = '8424584627:AAGGgqbpSOpGTZC_PITxcwVVjPv49qlYi-Q'
ADMIN_GROUP_ID = -5101530019  # ไอดีกลุ่มแอดมินสำหรับส่งสลิปไปตรวจสอบ
QR_IMAGE_URL = 'https://img2.pic.in.th/photo_2025-12-29_21-12-44.jpg'

# ลิ้งค์กลุ่มสำหรับแต่ละราคา
LINK_200 = "https://t.me/+m2H5MlD_04c2N2M1"
LINK_400 = "https://t.me/+6tEwQkfNvfc4ZTBl"
LINK_999 = "https://t.me/+m2H5MlD_04c2N2M1"

# ข้อความขอบคุณ (เหมือนกันทุกราคา)
THANK_YOU_TEXT = "ขอบคุณที่ซัพพอร์ต ฝากพิมพ์ +1 และ รีวิวในกลุ่ม VVIP ด้วยนะครับ"
# ===============================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ข้อความต้อนรับ
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1. ส่งข้อความรายละเอียด
    await context.bot.send_message(chat_id=update.effective_chat.id, text=WELCOME_TEXT)
    
    # 2. ส่งรูป QR Code จากลิ้งค์
    try:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id, 
            photo=QR_IMAGE_URL,
            caption="📸 สแกน QR Code เพื่อชำระเงิน\n\nโอนแล้ว **ส่งสลิป** เข้ามาในแชทนี้ได้เลยครับ แอดมินจะตรวจสอบสักครู่"
        )
    except Exception as e:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"เกิดข้อผิดพลาดในการโหลดรูป QR: {e}")

async def handle_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    username = user.username if user.username else "No Username"
    first_name = user.first_name if user.first_name else "ลูกค้า"
    
    # แจ้งลูกค้าว่าได้รับแล้ว
    await update.message.reply_text("⏳ ได้รับสลิปแล้วครับ รอแอดมินตรวจสอบและกดอนุมัติสักครู่นะครับ...")

    # สร้างปุ่ม 3 ปุ่มสำหรับแอดมิน (ฝัง user_id ไว้ในปุ่ม)
    keyboard = [
        [
            InlineKeyboardButton("✅ 200 บาท", callback_data=f"approve_200_{user_id}"),
            InlineKeyboardButton("✅ 400 บาท", callback_data=f"approve_400_{user_id}")
        ],
        [
            InlineKeyboardButton("✅ 999 บาท (ถาวร)", callback_data=f"approve_999_{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # ข้อความส่งหาแอดมิน
    caption_text = f"📩 สลิปใหม่จากลูกค้า!\nชื่อ: {first_name} (@{username})\nID: {user_id}\n\nตรวจสอบยอดแล้วกดปุ่มด้านล่าง:"
    
    # ส่งรูปสลิปไปที่กลุ่มแอดมิน
    try:
        await context.bot.send_photo(
            chat_id=ADMIN_GROUP_ID,
            photo=update.message.photo[-1].file_id,
            caption=caption_text,
            reply_markup=reply_markup
        )
    except Exception as e:
        print(f"Error sending slip to admin: {e}")

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer() # ตอบรับการกดปุ่ม

    data = query.data.split('_') # ข้อมูลรูปแบบ: action_price_userid
    action = data[0]
    price = data[1]
    customer_id = int(data[2])

    if action == "approve":
        invite_link = ""
        
        # เลือกลิ้งค์ตามราคา
        if price == "200":
            invite_link = LINK_200
        elif price == "400":
            invite_link = LINK_400
        elif price == "999":
            invite_link = LINK_999

        # ข้อความที่จะส่งให้ลูกค้า
        final_message = f"✅ ยอด {price} บาท อนุมัติเรียบร้อยครับ\n\nกดเข้ากลุ่มได้ที่นี่: {invite_link}\n\n{THANK_YOU_TEXT}"

        try:
            # 1. ส่งข้อความหาลูกค้า
            await context.bot.send_message(chat_id=customer_id, text=final_message)
            
            # 2. แก้ไขข้อความในกลุ่มแอดมินว่าใครเป็นคนกดอนุมัติ
            admin_name = query.from_user.first_name
            await query.edit_message_caption(
                caption=f"{query.message.caption}\n\n✅ อนุมัติยอด {price} แล้วโดย {admin_name}"
            )
        except Exception as e:
            # กรณีส่งหาลูกค้าไม่ได้ (เช่น บล็อกบอท)
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"⚠️ ส่งลิ้งค์ให้ลูกค้า ID {customer_id} ไม่สำเร็จ: {e}")

if __name__ == '__main__':
    print("Starting Bot...")
    application = ApplicationBuilder().token(TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.PHOTO, handle_slip))
    application.add_handler(CallbackQueryHandler(button_click))

    print("Bot is running...")
    application.run_polling()
