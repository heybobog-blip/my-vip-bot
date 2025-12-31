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

# ลิ้งก์ QR Code ของคุณ
QR_IMAGE_URL = 'https://img2.pic.in.th/photo_2025-12-29_21-12-44.jpg'

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
    {"id": -1003465527678, "name": "VVIP V2"},
]

THANK_YOU_TEXT = "ขอบคุณที่ซัพพอร์ต ฝากพิมพ์ +1 และ รีวิวในกลุ่ม VVIP ด้วยนะครับ"

# =========================================================
# ระบบเช็คซอง TrueMoney (อัปเกรด Header แก้ Server Error)
# =========================================================
def redeem_truemoney(url, phone_number):
    try:
        # 1. ตรวจสอบลิ้งก์
        match = re.search(r'v=([a-zA-Z0-9]+)', url)
        if not match: return {"status": "error", "message": "ลิ้งก์ผิดรูปแบบ"}
        voucher_code = match.group(1)
        
        # 2. ตั้งค่าหัวข้อความให้เหมือนคนใช้ Chrome จริงๆ (แก้ Server Error)
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json',
            'Origin': 'https://gift.truemoney.com',
            'Referer': 'https://gift.truemoney.com/'
        }
        
        payload = {"mobile": phone_number, "voucher_hash": voucher_code}
        
        # 3. ส่งคำขอไป TrueMoney
        response = requests.post(
            f"https://gift.truemoney.com/campaign/vouchers/{voucher_code}/redeem", 
            json=payload, headers=headers, timeout=30
        )
        
        # 4. อ่านผลลัพธ์ (ดักจับ Error กรณีอ่าน JSON ไม่ได้)
        try:
            data = response.json()
        except json.JSONDecodeError:
            return {"status": "error", "message": f"Server TrueMoney ไม่ตอบสนอง (Code: {response.status_code})"}

        # 5. ตรวจสอบสถานะ
        if data.get('status', {}).get('code') == 'SUCCESS':
            d = data.get('data', {})
            amt = float(d.get('my_ticket', {}).get('amount_baht', 0))
            sender = d.get('owner_profile', {}).get('nickname', 'ไม่ระบุ')
            return {"status": "success", "amount": int(amt), "sender": sender}
        else:
            return {"status": "error", "message": data.get('status', {}).get('code', 'Unknown Error')}
            
    except Exception as e: 
        return {"status": "error", "message": str(e)}

# =========================================================
# ส่วนแสดงผล (Frontend & Menu)
# =========================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    TEXT = """
🔥 **VVIP By.เซียนจู — ยินดีต้อนรับครับ** 🔥

💎 **เรทราคาค่าเข้า**
▪️ **200.-** (ดูอย่างเดียว)
▪️ **400.-** (ดู + เซฟได้ 💾)
🏆 **999.-** (เหมาถาวร เข้าทุกกลุ่ม)

👇 **กรุณาเลือกวิธีการซื้อ:**
"""
    keyboard = [
        [InlineKeyboardButton("🧧 ซื้อแบบซอง (เข้ากลุ่มอัตโนมัติ)", callback_data="mode_gift")],
        [InlineKeyboardButton("🏦 ซื้อแบบสแกน QR (โอนธนาคาร)", callback_data="mode_qr")],
        [InlineKeyboardButton("💬 ซื้อกับแอดมิน 1", url="https://t.me/ZeinJu001")],
        [InlineKeyboardButton("💬 ซื้อกับแอดมิน 2", url="https://t.me/duded16")]
    ]
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=TEXT,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    # 1. กดปุ่มแบบซอง
    if data == "mode_gift":
        text = """
🧧 **วิธีจ่ายด้วยซองของขวัญ (ระบบออโต้)**

1. เข้าแอป TrueMoney เลือก "ส่งซองของขวัญ"
2. ใส่ยอดเงิน (200, 400, 999)
3. เลือก "แบ่งจำนวนเงินเท่ากัน"
4. จำนวนคนรับซอง: **1 คน**
5. **ส่งลิ้งก์ซอง** มาในแชทนี้ได้เลยครับ

(ระบบจะดึงเข้ากลุ่มทันที ไม่ต้องรอแอดมิน)
"""
        await query.message.reply_text(text)

    # 2. กดปุ่มแบบ QR (ไม่โชว์เบอร์แล้ว ตามที่ขอ)
    elif data == "mode_qr":
        caption = """
📸 **สแกน QR Code นี้เพื่อชำระเงิน**

เมื่อโอนเสร็จแล้ว ให้ส่ง **"รูปสลิป"** เข้ามาในแชทนี้ครับ
(แอดมินจะตรวจสอบและกดอนุมัติให้ครับ)
"""
        await context.bot.send_photo(
            chat_id=query.from_user.id,
            photo=QR_IMAGE_URL,
            caption=caption,
            parse_mode='Markdown'
        )

    # 3. แอดมินกดอนุมัติ (หลังบ้าน)
    elif data.startswith("ap_"):
        try:
            _, price, user_id = data.split('_')
            user_id = int(user_id)
            
            if price == "999":
                kb = []
                for g in ALL_ACCESS_ROOMS:
                    l = await context.bot.create_chat_invite_link(g["id"], member_limit=1, name=f"Man999_{user_id}")
                    kb.append([InlineKeyboardButton(f"เข้า {g['name']}", url=l.invite_link)])
                await context.bot.send_message(user_id, "✅ **แอดมินอนุมัติแล้ว (999)**\nกดเข้ากลุ่มด้านล่าง:", reply_markup=InlineKeyboardMarkup(kb))
            
            elif price in SELECTABLE_ROOMS:
                kb = []
                for r in SELECTABLE_ROOMS[price]:
                    kb.append([InlineKeyboardButton(f"เลือก {r['name']}", callback_data=f"sel_{r['id']}_{price}")])
                await context.bot.send_message(user_id, f"✅ **แอดมินอนุมัติแล้ว ({price})**\nเลือกห้องที่ต้องการ:", reply_markup=InlineKeyboardMarkup(kb))

            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **อนุมัติเรียบร้อย**")
        except:
            await query.message.reply_text("❌ ผิดพลาด (บอทอาจไม่ได้เป็นแอดมิน)")

    # 4. ลูกค้าเลือกห้อง
    elif data.startswith("sel_"):
        _, gid, price = data.split('_')
        try:
            link = await context.bot.create_chat_invite_link(int(gid), member_limit=1, name=f"Final_{price}")
            kb = [[InlineKeyboardButton("⭐️ กดเข้ากลุ่มที่นี่ ⭐️", url=link.invite_link)]]
            await query.edit_message_text(f"✅ **เลือกห้องเรียบร้อย**\nกดปุ่มด้านล่างเพื่อเข้าห้อง:", reply_markup=InlineKeyboardMarkup(kb))
            await context.bot.send_message(query.from_user.id, THANK_YOU_TEXT)
        except:
            await query.message.reply_text("❌ สร้างลิ้งก์ไม่สำเร็จ")

# รับรูปสลิป (QR Mode) -> ส่งให้แอดมินกด
async def handle_slip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    kb = [
        [InlineKeyboardButton("✅ 200", callback_data=f"ap_200_{user.id}"),
         InlineKeyboardButton("✅ 400", callback_data=f"ap_400_{user.id}")],
        [InlineKeyboardButton("🏆 999", callback_data=f"ap_999_{user.id}")]
    ]
    caption = f"📩 **สลิปใหม่**\nจาก: {user.first_name}\nID: `{user.id}`\n\nตรวจสอบยอดแล้วกดปุ่ม:"
    
    await context.bot.send_photo(ADMIN_GROUP_ID, update.message.photo[-1].file_id, caption=caption, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    await update.message.reply_text("⏳ **ได้รับสลิปแล้ว** รอแอดมินกดยืนยันสักครู่นะครับ...")

# รับลิ้งก์ซอง (Gift Mode) -> ออโต้ 100%
async def handle_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    user = update.message.from_user
    msg = await update.message.reply_text("🤖 กำลังตรวจสอบซอง...")
    
    res = await asyncio.to_thread(redeem_truemoney, link, MY_PHONE_NUMBER)
    
    if res['status'] == 'success':
        amt = res['amount']
        try: await context.bot.send_message(ADMIN_GROUP_ID, f"💰 **Auto Success!**\nUser: {user.first_name}\nยอด: {amt}")
        except: pass
        
        if amt >= 999:
            kb = []
            for g in ALL_ACCESS_ROOMS:
                l = await context.bot.create_chat_invite_link(g["id"], member_limit=1, name=f"Auto999_{user.id}")
                kb.append([InlineKeyboardButton(f"เข้า {g['name']}", url=l.invite_link)])
            await msg.edit_text(f"✅ **รับยอด {amt} เรียบร้อย**", reply_markup=InlineKeyboardMarkup(kb))
        elif str(amt) in SELECTABLE_ROOMS:
            kb = []
            for r in SELECTABLE_ROOMS[str(amt)]:
                kb.append([InlineKeyboardButton(f"เลือก {r['name']}", callback_data=f"sel_{r['id']}_{amt}")])
            await msg.edit_text(f"✅ **รับยอด {amt} เรียบร้อย**\nเลือกห้อง:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await msg.edit_text(f"✅ รับยอด {amt} บาท (ยอดไม่ตรงแพ็กเกจ) ติดต่อแอดมิน")
    else:
        await msg.edit_text(f"❌ **ทำรายการไม่ได้**\nเหตุผล: {res['message']}")

# ===========================================================
# Server (บังคับสร้างบอทใหม่ทุกครั้ง ป้องกันบอทหลับ)
# ===========================================================
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        try: update_data = json.loads(post_body.decode('utf-8'))
        except: self.send_response(500); self.end_headers(); return

        async def main():
            app = ApplicationBuilder().token(TOKEN).build()
            app.add_handler(CommandHandler('start', start))
            app.add_handler(MessageHandler(filters.Regex("gift.truemoney.com"), handle_gift))
            app.add_handler(MessageHandler(filters.PHOTO, handle_slip))
            app.add_handler(CallbackQueryHandler(button_click))
            async with app: await app.process_update(Update.de_json(update_data, app.bot))

        try: asyncio.run(main())
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); loop.run_until_complete(main())
        except Exception as e: print(e)

        self.send_response(200); self.end_headers(); self.wfile.write(b'OK')
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"Bot OK")
