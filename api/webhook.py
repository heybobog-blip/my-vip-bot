import os
import json
import asyncio
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler

# =================ตั้งค่าข้อมูลระบบ=================
TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_GROUP_ID = -1003614142313
MY_PHONE_NUMBER = "0659325591" 

# =================ตั้งค่าห้อง=================
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
]

THANK_YOU_TEXT = "ขอบคุณที่ซัพพอร์ต ฝากพิมพ์ +1 และ รีวิวในกลุ่ม VVIP ด้วยนะครับ"
application = ApplicationBuilder().token(TOKEN).build()

# =========================================================
# ฟังก์ชันแกะซอง TrueMoney
# =========================================================
def redeem_truemoney(url, phone_number):
    try:
        match = re.search(r'v=([a-zA-Z0-9]+)', url)
        if not match:
            return {"status": "error", "message": "รูปแบบลิ้งก์ไม่ถูกต้อง"}
        
        voucher_code = match.group(1)
        
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Origin': 'https://gift.truemoney.com',
            'Referer': 'https://gift.truemoney.com/'
        }
        
        payload = {"mobile": phone_number, "voucher_hash": voucher_code}
        
        response = requests.post(
            f"https://gift.truemoney.com/campaign/vouchers/{voucher_code}/redeem", 
            json=payload, headers=headers, timeout=20
        )
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            if response.status_code != 200:
                return {"status": "error", "message": f"Server Error ({response.status_code})"}
            return {"status": "error", "message": "Invalid Response"}

        if 'status' in data and data['status']['code'] == 'SUCCESS':
            amount = float(data['data']['my_ticket']['amount_baht'])
            sender_name = data['data']['owner_profile']['nickname']
            return {"status": "success", "amount": int(amount), "sender": sender_name}
        
        elif 'status' in data:
            code = data['status']['code']
            if code == 'CANNOT_GET_OWN_VOUCHER': return {"status": "error", "message": "ไม่สามารถรับซองของตัวเองได้"}
            if code == 'TARGET_USER_REDEEMED': return {"status": "error", "message": "ซองนี้ถูกรับไปแล้ว"}
            if code == 'VOUCHER_OUT_OF_STOCK': return {"status": "error", "message": "ซองนี้หมดแล้ว"}
            return {"status": "error", "message": f"รับเงินไม่ได้: {code}"}
            
        else:
            return {"status": "error", "message": f"Unknown Error ({response.status_code})"}

    except Exception as e:
        return {"status": "error", "message": str(e)}

# =========================================================
# Bot Handlers
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
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text=WELCOME_TEXT, 
        reply_markup=InlineKeyboardMarkup(keyboard), 
        parse_mode='Markdown'
    )

async def reject_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ **ไม่รับสลิป/QR Code**\nกรุณาส่ง **ลิ้งก์ซองของขวัญ TrueMoney** เท่านั้นครับ")

async def handle_truemoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    user = update.message.from_user
    
    msg = await update.message.reply_text("🤖 กำลังตรวจสอบซองและยอดเงิน...")

    result = await asyncio.to_thread(redeem_truemoney, link, MY_PHONE_NUMBER)

    if result['status'] == 'success':
        amount = result['amount']
        
        try:
            admin_text = f"💰 **บอทรับเงินสำเร็จ!**\nUser: {user.first_name}\nยอด: {amount}.-"
            await context.bot.send_message(chat_id=ADMIN_GROUP_ID, text=admin_text)
        except: pass

        if amount >= 999:
            kb = []
            for g in ALL_ACCESS_ROOMS:
                link = await context.bot.create_chat_invite_link(g["id"], member_limit=1, name=f"Auto999_{user.id}")
                kb.append([InlineKeyboardButton(f"เข้า {g['name']}", url=link.invite_link)])
            await msg.edit_text(f"✅ **ได้รับ {amount} บาท (เหมาถาวร)**\nกดเข้ากลุ่มด้านล่าง:", reply_markup=InlineKeyboardMarkup(kb))
            
        elif str(amount) in SELECTABLE_ROOMS:
            kb = []
            for r in SELECTABLE_ROOMS[str(amount)]:
                kb.append([InlineKeyboardButton(f"เลือก {r['name']}", callback_data=f"sel_{r['id']}_{amount}")])
            await msg.edit_text(f"✅ **ได้รับ {amount} บาท**\nเลือกห้องที่ต้องการเข้า (ได้ 1 ห้อง):", reply_markup=InlineKeyboardMarkup(kb))
            
        else:
            await msg.edit_text(f"✅ ได้รับ {amount} บาท (ยอดไม่ตรงแพ็กเกจ) โปรดติดต่อแอดมิน")
            
    else:
        contact_kb = [[InlineKeyboardButton("💬 แจ้งแอดมิน", url="https://t.me/ZeinJu001")]]
        await msg.edit_text(f"❌ **ทำรายการไม่สำเร็จ**\nสาเหตุ: {result['message']}\n\n(หากเงินถูกตัดไปแล้ว ให้แคปจอนี้แจ้งแอดมินครับ)", reply_markup=InlineKeyboardMarkup(contact_kb))

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("sel_"):
        _, gid, price = data.split('_')
        try:
            link = await context.bot.create_chat_invite_link(int(gid), member_limit=1, name=f"AutoSel_{price}")
            kb = [[InlineKeyboardButton("⭐️ กดเข้ากลุ่มที่นี่ ⭐️", url=link.invite_link)]]
            await query.edit_message_text(f"✅ **เลือกห้องเรียบร้อย**\nกดปุ่มด้านล่างเพื่อเข้าห้อง:", reply_markup=InlineKeyboardMarkup(kb))
            await context.bot.send_message(query.from_user.id, THANK_YOU_TEXT)
        except Exception as e:
            await query.message.reply_text("❌ เกิดข้อผิดพลาด (บอทอาจไม่ได้เป็นแอดมินกลุ่มนั้น)")

# ===========================================================
# ส่วน Server (แบบ Debug: ถ้าพังจะฟ้อง Error ออกมา)
# ===========================================================
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        
        try:
            json_string = post_body.decode('utf-8')
            update_data = json.loads(json_string)
            print(f"📩 รับข้อความ: {json_string[:50]}...")
        except Exception as e:
            print(f"❌ Error JSON: {e}")
            self.send_response(500)
            self.end_headers()
            return

        async def main():
            try:
                async with application:
                    update = Update.de_json(update_data, application.bot)
                    await application.process_update(update)
            except Exception as e:
                print(f"❌ บอทพัง (Runtime Error): {e}")

        try:
            asyncio.run(main())
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
        except Exception as e:
            print(f"❌ Async Error: {e}")

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Running!")
