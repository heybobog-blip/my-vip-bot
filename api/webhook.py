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
GROUP_ID_200V2 = -1003578310056  # ใส่เลขกลุ่มใหม่

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
    await query.answer()

    data = query.data.split('_')
    price = data[1]
    customer_id = int(data[2])

    # ==================================================================
    # [จุดแก้] กำหนดว่าราคาไหน จะได้เข้ากลุ่มไหนบ้าง
    # ==================================================================
    target_groups = [] # สร้างลิสต์รายการกลุ่มที่จะส่งให้ลูกค้า

    if price == "200":
        # ราคา 200 ได้เข้ากลุ่มเดียว
        target_groups.append({"id": GROUP_ID_200, "name": "ห้อง 200"}) 
        
    elif price == "400":
        # ราคา 400 ได้เข้ากลุ่มเดียว
        target_groups.append({"id": GROUP_ID_400, "name": "ห้อง 400"})
        
    else: # กรณี 999 (เหมาหมด) หรือ VIP
        # -----------------------------------------------------------
        # ถ้ามีกลุ่มใหม่เพิ่ม ให้ Copy บรรทัดข้างล่าง แล้วเปลี่ยนชื่อตัวแปรกลุ่มครับ
        # -----------------------------------------------------------
        target_groups.append({"id": GROUP_ID_200, "name": "ห้อง 200"})
        target_groups.append({"id": GROUP_ID_400, "name": "ห้อง 400"})
        target_groups.append({"id": GROUP_ID_999, "name": "ห้อง VIP"})
        # target_groups.append({"id": GROUP_ID_NEW, "name": "ห้องน้องใหม่"})  <-- ใส่เพิ่มตรงนี้
        target_groups.append({"id": GROUP_ID_200V2, "name": "ห้องน้องใหม่"})
        
    # ==================================================================

    try:
        keyboard = []
        
        # วนลูปสร้างลิ้งก์ตามจำนวนกลุ่มที่อยู่ในลิสต์
        for group in target_groups:
            # สร้างลิ้งก์แบบเข้าครั้งเดียว
            invite_link_obj = await context.bot.create_chat_invite_link(
                chat_id=group["id"], 
                member_limit=1, 
                name=f"VVIP {price} Slip {customer_id}"
            )
            
            # สร้างปุ่มสำหรับกลุ่มนั้นๆ
            btn_text = f"⭐️ กดเข้า {group['name']}"
            keyboard.append([InlineKeyboardButton(btn_text, url=invite_link_obj.invite_link)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        final_message = f"✅ ยอด {price} บาท อนุมัติเรียบร้อยครับ\n\n👇 กดปุ่มด้านล่างเพื่อเข้ากลุ่มได้เลยครับ\n(แยกลิ้งก์ตามกลุ่ม กดเข้าให้ครบนะครับ)\n\n{THANK_YOU_TEXT}"

        # ส่งข้อความหาลูกค้า
        await context.bot.send_message(
            chat_id=customer_id, 
            text=final_message, 
            reply_markup=reply_markup,
            protect_content=True
        )
        
        # แก้ไขข้อความในห้องแอดมิน
        await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ อนุมัติยอด {price} เรียบร้อย\n(ส่งไป {len(target_groups)} ลิ้งก์)")

    except Exception as e:
        print(f"Error generating link or replying: {e}")
        error_text = f"❌ เกิดข้อผิดพลาด: บอทอาจยังไม่ได้เป็น Admin ในกลุ่มเป้าหมาย หรือเลขกลุ่มผิด ({e})"
        await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=error_text)
