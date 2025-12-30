import os
import json
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler

# =================ตั้งค่าข้อมูลระบบ=================
TOKEN = os.environ.get("TELEGRAM_TOKEN")

# [อัปเดต] ใส่เลขห้องแอดมินตัวใหม่ที่บอกมาครับ
ADMIN_GROUP_ID = -1003614142313

QR_IMAGE_URL = 'https://img2.pic.in.th/photo_2025-12-29_21-12-44.jpg'
THANK_YOU_TEXT = "ขอบคุณที่ซัพพอร์ต ฝากพิมพ์ +1 และ รีวิวในกลุ่ม VVIP ด้วยนะครับ"

# =========================================================
# [ตั้งค่าห้องลูกค้า]
# =========================================================
SELECTABLE_ROOMS = {
    "200": [
        {"id": -1003465527678, "name": "VVIP V1"},
        # {"id": -1003465527678, "name": "VVIP V2"} # เพิ่มห้องได้
    ],
    "400": [
        {"id": -1003477489997, "name": "VVIP V1 SAVE"}
    ]
}

ALL_ACCESS_ROOMS = [
    {"id": -1003477489997, "name": "VVIP V1 SAVE"},
    # {"id": -1003465527678, "name": "VVIP V1"}, # ถ้าจะแจกห้องนี้ด้วยให้เอา # ออก
]

# เตรียมบอท
application = ApplicationBuilder().token(TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ข้อความต้อนรับ (แบบที่เลือกไว้)
    WELCOME_TEXT = """
🔥 VVIP By.เซียนจู — ทีเด็ดงานดี ห้ามพลาด! 🔥

👇 เรทราคาค่าเข้า
✅ 200 บาท : ดูในกลุ่ม (เซฟไม่ได้)
✅ 400 บาท : ดู + เซฟลงเครื่องได้ 💾

🚀 PROMOTION เหมาจบ!!
🏆 999 บาท (VIP ถาวร)
เข้าได้ทุกห้อง! ทั้งห้องหลัก ห้อง Save และห้องใหม่
(จ่ายครั้งเดียว จบเลย ไม่ต้องจ่ายเพิ่ม)

👀 ดูตัวอย่างงานก่อนตัดสินใจ
https://t.me/+5sWrRGBIm3Y5ODE1

🛡 เครดิตแน่น รีวิวเพียบ
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
# ฟังก์ชันจัดการ: รูปภาพสลิป
# ---------------------------------------------------------
async def handle_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    user_id = user.id
    name = user.first_name
    
    await update.message.reply_text("⏳ ได้รับสลิปแล้วครับ รอแอดมินตรวจสอบสักครู่นะครับ...")
    
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
        # ส่งไปห้องแอดมินใหม่
        await context.bot.send_photo(
            chat_id=ADMIN_GROUP_ID, 
            photo=update.message.photo[-1].file_id, 
            caption=caption_text, 
            reply_markup=reply_markup
        )
    except Exception as e:
        error_msg = f"❌ ส่งสลิปไปห้องแอดมินไม่ได้: {e}\n(เช็คว่าบอทอยู่ในกลุ่ม {ADMIN_GROUP_ID} หรือยัง?)"
        print(error_msg)
        # แจ้งเตือนแอดมินถ้าทำได้ หรือปล่อยผ่านลง log

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

# ---------------------------------------------------------
# ฟังก์ชันจัดการปุ่มกด
# ---------------------------------------------------------
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data

    # >>> แอดมินกดอนุมัติ
    if data.startswith("admin_approve_"):
        try:
            _, _, price, customer_id = data.split('_')
            customer_id = int(customer_id)

            # กรณี 999 (เหมา)
            if price == "999":
                links_keyboard = []
                for group in ALL_ACCESS_ROOMS:
                    invite = await context.bot.create_chat_invite_link(
                        chat_id=group["id"],
                        member_limit=1,
                        name=f"VVIP 999 Access"
                    )
                    links_keyboard.append([InlineKeyboardButton(f"เข้า {group['name']}", url=invite.invite_link)])
                
                final_markup = InlineKeyboardMarkup(links_keyboard)
                
                await context.bot.send_message(
                    chat_id=customer_id,
                    text=f"✅ **ยอด 999 บาท อนุมัติแล้วครับ**\n\nคุณได้รับสิทธิ์เข้าทุกห้อง กดเข้าให้ครบทุกปุ่มนะครับ\n\n{THANK_YOU_TEXT}",
                    reply_markup=final_markup
                )
                admin_status_text = "✅ อนุมัติ 999 (ส่งครบทุกห้องแล้ว)"

            # กรณี 200/400 (เลือกเอง)
            else:
                rooms = SELECTABLE_ROOMS.get(price, [])
                if not rooms:
                    await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"❌ ไม่พบห้องสำหรับราคา {price}")
                    return

                customer_keyboard = []
                for room in rooms:
                    btn_text = f"เลือกเข้า {room['name']}"
                    callback_str = f"select_room_{room['id']}_{price}"
                    customer_keyboard.append([InlineKeyboardButton(btn_text, callback_data=callback_str)])
                
                cust_markup = InlineKeyboardMarkup(customer_keyboard)
                
                await context.bot.send_message(
                    chat_id=customer_id,
                    text=f"✅ **ยอด {price} บาท อนุมัติแล้วครับ**\n\n👇 กรุณากดเลือกห้องที่ต้องการเข้า (เลือกได้ 1 ห้องเท่านั้น):",
                    reply_markup=cust_markup
                )
                admin_status_text = f"✅ อนุมัติ {price} แล้ว (รอเกสเลือกห้อง)"

            # อัปเดตข้อความห้องแอดมิน
            if query.message.caption:
                await query.edit_message_caption(caption=f"{query.message.caption}\n\n{admin_status_text}")
            else:
                await query.edit_message_text(text=f"{query.message.text}\n\n{admin_status_text}")

        except Exception as e:
            print(f"Admin Error: {e}")
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=f"❌ Error: {e}")

    # >>> ลูกค้ากดเลือกห้อง
    elif data.startswith("select_room_"):
        try:
            parts = data.split('_')
            target_group_id = int(parts[2])
            price_label = parts[3]

            invite_link_obj = await context.bot.create_chat_invite_link(
                chat_id=target_group_id, 
                member_limit=1, 
                name=f"VVIP {price_label} Selected"
            )
            
            link_keyboard = [[InlineKeyboardButton("⭐️ กดเข้ากลุ่มที่นี่ ⭐️", url=invite_link_obj.invite_link)]]
            link_markup = InlineKeyboardMarkup(link_keyboard)
            
            await query.edit_message_text(
                text=f"✅ **เลือกห้องเรียบร้อย**\n\nกดปุ่มด้านล่างเพื่อเข้าห้องได้เลยครับ:\n(ลิ้งก์ใช้ได้ครั้งเดียว)",
                reply_markup=link_markup
            )
            
            await context.bot.send_message(chat_id=query.from_user.id, text=THANK_YOU_TEXT)

        except Exception as e:
            print(f"Customer Error: {e}")
            await context.bot.send_message(chat_id=query.from_user.id, text="❌ เกิดข้อผิดพลาด (บอทอาจไม่ได้เป็นแอดมินในกลุ่มปลายทาง)")

# ===========================================================
# Server
# ===========================================================

application.add_handler(CommandHandler('start', start))
application.add_handler(MessageHandler(filters.PHOTO, handle_slip))
application.add_handler(MessageHandler(filters.TEXT & filters.Regex("gift.truemoney.com"), handle_truemoney))
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
