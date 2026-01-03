import os
import json
import asyncio
import re
import requests
import random
from datetime import datetime
import pytz 
import gspread # เพิ่มตัวนี้
from oauth2client.service_account import ServiceAccountCredentials # เพิ่มตัวนี้
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler

# =================ตั้งค่าข้อมูลระบบ=================
TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_GROUP_ID = -1003614142313 
MY_PHONE_NUMBER = "0659325591"  

# ชื่อไฟล์ Google Sheet ที่คุณตั้งไว้ (ต้องตรงเป๊ะๆ)
SHEET_NAME = "VVIP_Data" 

# =================ตั้งค่าห้อง=================
SELECTABLE_ROOMS = {
    "200": [
        {"id": -1003465527678, "name": "VVIP V1 (200)"},
    ],
    "400": [
        {"id": -1003477489997, "name": "VVIP V1 SAVE (400)"}
    ]
}

ALL_ACCESS_ROOMS = [
    {"id": -1003477489997, "name": "VVIP V1 SAVE"},
]

THANK_YOU_TEXT = "ขอบคุณที่ซัพพอร์ตครับ ฝากพิมพ์ +1 และ รีวิวในกลุ่มด้วยนะครับ ❤️"

# =========================================================
# ฟังก์ชันบันทึกลง Google Sheet
# =========================================================
def save_to_google_sheet(data_row):
    try:
        # ดึงกุญแจจาก Vercel Environment Variable
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        if not creds_json:
            print("❌ ไม่พบ GOOGLE_CREDENTIALS ในตั้งค่า Vercel")
            return

        # เชื่อมต่อ Google Sheets
        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        # เปิดไฟล์ Sheet
        sheet = client.open(SHEET_NAME).sheet1
        
        # เพิ่มแถวใหม่
        sheet.append_row(data_row)
        print("✅ บันทึกข้อมูลลง Sheet เรียบร้อย")
        
    except Exception as e:
        print(f"❌ บันทึก Sheet ไม่สำเร็จ: {e}")

# =========================================================
# ระบบเช็คซอง 
# =========================================================
def redeem_truemoney(url, phone_number):
    try:
        match = re.search(r'v=([a-zA-Z0-9]+)', url)
        if not match: return {"status": "error", "message": "ลิ้งก์ผิดรูปแบบ"}
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
            json=payload, headers=headers, timeout=30
        )
        
        try:
            data = response.json()
        except json.JSONDecodeError:
            return {"status": "error", "message": f"Server TrueMoney ไม่ตอบสนอง ({response.status_code})"}

        if data.get('status', {}).get('code') == 'SUCCESS':
            d = data.get('data', {})
            amt = float(d.get('my_ticket', {}).get('amount_baht', 0))
            full_name = d.get('owner_profile', {}).get('nickname', 'ไม่ระบุ')
            voucher_hash = d.get('voucher', {}).get('voucher_id', voucher_code) 

            name_parts = full_name.split()
            if len(name_parts) > 1:
                masked_name = f"{name_parts[0]} ***"
            else:
                masked_name = full_name
            
            return {
                "status": "success", 
                "amount": int(amt), 
                "sender_masked": masked_name,
                "full_name": full_name, # ส่งชื่อเต็มไปบันทึก
                "hash": voucher_hash
            }
        else:
            return {"status": "error", "message": data.get('status', {}).get('code', 'Unknown Error')}
            
    except Exception as e: 
        return {"status": "error", "message": str(e)}

# =========================================================
# ส่วนแสดงผล (Frontend)
# =========================================================

async def send_main_menu(update, context, is_edit=False):
    TEXT = """
✨ **ยินดีต้อนรับสู่...** ✨
🔥 **VVIP 18+ คุยได้ (เจริญPORN)** 🔥
━━━━━━━━━━━━━━━━━━
💎 **RATE PRICE (แพ็กเกจ)** 💎

👑 **999 บาท (SSSVIP) 🔥🔥🔥**
└ คุ้มที่สุด! จ่ายครั้งเดียวจบ เข้าได้ทุกกลุ่มยันชาติหน้า

🥈 **400 บาท (SVIP)**
└ สายเก็บ เซฟได้ไม่อั้น (กลุ่ม Save)

🥉 **200 บาท (VIP)**
└ กลุ่มธรรมดา (ดูได้อย่างเดียว เซฟไม่ได้)
━━━━━━━━━━━━━━━━━━
🤖 **ระบบจ่ายเงินอัตโนมัติ (Auto Bot)** 🤖
รวดเร็ว ไม่ต้องรอแอดมินตอบ!
📝 **วิธีใช้งานบอทชำระเงิน**
`1. กดปุ่ม "จ่ายด้วยซอง TrueMoney"`
`2. อ่านวิธีทำซอง และสร้างลิงก์`
`3. ส่งลิงก์ซองเข้ามาในแชทนี้`

❓ **ติดปัญหา / มีคำถาม?**
หากโอนเงินแล้วไม่ได้รับลิ้งค์ หรือต้องการสอบถามเพิ่มเติม
👉 **กดปุ่ม "ซื้อกับแอดมิน" ด้านล่าง เพื่อติดต่อแอดมินโดยตรงครับ** 👇
"""
    keyboard = [
        [InlineKeyboardButton("🧧 จ่ายด้วยซอง TrueMoney (Auto 🚀)", callback_data="mode_gift")],
        [InlineKeyboardButton("🛒 ซื้อกับแอดมิน 1", url="https://t.me/ZeinJu001"), InlineKeyboardButton("🛒 ซื้อกับแอดมิน 2", url="https://t.me/duded16")],
        [InlineKeyboardButton("⭐️ เช็คเครดิต", url="https://t.me/+uoEnKbH_PP05NWQ1"), InlineKeyboardButton("🎥 กลุ่มตัวอย่าง", url="https://t.me/+5sWrRGBIm3Y5ODE1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if is_edit:
        await update.callback_query.edit_message_text(text=TEXT, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=TEXT, reply_markup=reply_markup, parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update, context, is_edit=False)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "mode_gift":
        text = """
📝 **วิธีชำระเงินด้วยซองของขวัญ (ระบบออโต้)**
➖➖➖➖➖➖➖➖➖➖
1️⃣ เข้าแอป TrueMoney Wallet เลือกเมนู **'ซองของขวัญ'**
2️⃣ ใส่ยอดเงินตามแพ็กเกจที่เลือก **(200, 400 หรือ 999)**
3️⃣ เลือกประเภท **'แบ่งจำนวนเงินเท่ากัน'**
4️⃣ ใส่จำนวนคนรับเป็น **1 คน**
5️⃣ กดสร้างซอง > **คัดลอกลิ้งก์**

🚀 **นำลิ้งก์มาวางส่งในแชทนี้ได้เลยครับ ระบบจะดึงเข้ากลุ่มทันที**
"""
        kb = [[InlineKeyboardButton("🔙 กลับเมนูหลัก", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

    elif data == "back_main":
        await send_main_menu(update, context, is_edit=True)

    elif data.startswith("sel_"):
        try:
            _, gid, price = data.split('_')
            rnd = random.randint(1000,9999)
            link_name = f"User_{user_id}_{price}_{rnd}"
            link = await context.bot.create_chat_invite_link(chat_id=int(gid), member_limit=1, name=link_name)
            kb = [[InlineKeyboardButton("⭐️ กดเข้ากลุ่มที่นี่ ⭐️", url=link.invite_link)]]
            await query.edit_message_text(f"✅ **เลือกห้องเรียบร้อย**\nกดปุ่มด้านล่างเพื่อเข้าห้อง:\n(ลิ้งก์ใช้ได้ครั้งเดียว)", reply_markup=InlineKeyboardMarkup(kb))
            await context.bot.send_message(user_id, THANK_YOU_TEXT)
        except Exception as e:
            await query.message.reply_text("❌ สร้างลิ้งก์ไม่สำเร็จ")

async def handle_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    user = update.message.from_user
    msg = await update.message.reply_text("🤖 กำลังตรวจสอบซอง...")
    
    res = await asyncio.to_thread(redeem_truemoney, link, MY_PHONE_NUMBER)
    
    if res['status'] == 'success':
        amt = res['amount']
        sender_masked = res['sender_masked']
        full_name = res.get('full_name', 'ไม่ระบุ')
        v_hash = res.get('hash', 'N/A')
        
        # --- เตรียมข้อมูลเวลา ---
        tz = pytz.timezone('Asia/Bangkok')
        now_str = datetime.now(tz).strftime('%d/%m/%Y %H:%M:%S')

        # --- 📝 บันทึกลง Google Sheet (ทำงานเบื้องหลัง) ---
        sheet_data = [
            now_str,                # A: เวลา
            amt,                    # B: ยอดเงิน
            user.first_name,        # C: ชื่อลูกค้าใน Telegram
            str(user.id),           # D: ID ลูกค้า
            full_name,              # E: ชื่อ TrueMoney (ชื่อเต็ม)
            v_hash                  # F: Hash
        ]
        # เรียกฟังก์ชันบันทึก
        await asyncio.to_thread(save_to_google_sheet, sheet_data)
        
        # --- ส่งรายงานแอดมิน ---
        admin_report = f"""
🎁 **รายงานรับซอง (Auto)**
🕒 เวลา: {now_str}

💰 **ข้อมูลการเงิน**
💵 ยอดเงิน: {amt} บาท
👤 ชื่อทรูมันนี่: {sender_masked}
🎫 Hash: `{v_hash}`

👤 **ข้อมูลลูกค้า**
📛 ชื่อ: {user.first_name}
🆔 User: @{user.username if user.username else 'ไม่ระบุ'}
🔢 ID: `{user.id}`
⭐ สถานะ: User ทั่วไป

สถานะ: ✅ **บอทอนุมัติแล้ว ({amt})**
"""
        try: await context.bot.send_message(ADMIN_GROUP_ID, admin_report, parse_mode='Markdown')
        except: pass
        
        # --- ส่งของให้ลูกค้า ---
        rnd = random.randint(1000,9999)
        if amt >= 999:
            kb = []
            for g in ALL_ACCESS_ROOMS:
                l = await context.bot.create_chat_invite_link(chat_id=g["id"], member_limit=1, name=f"Auto999_{user.id}_{rnd}")
                kb.append([InlineKeyboardButton(f"เข้า {g['name']}", url=l.invite_link)])
            await msg.edit_text(f"✅ **รับยอด {amt} เรียบร้อย**", reply_markup=InlineKeyboardMarkup(kb))
        elif str(amt) in SELECTABLE_ROOMS:
            kb = []
            for r in SELECTABLE_ROOMS[str(amt)]:
                kb.append([InlineKeyboardButton(f"เลือก {r['name']}", callback_data=f"sel_{r['id']}_{amt}")])
            await msg.edit_text(f"✅ **รับยอด {amt} เรียบร้อย**\nเลือกห้อง:", reply_markup=InlineKeyboardMarkup(kb))
        else:
            await msg.edit_text(f"✅ รับยอด {amt} บาท (ยอดไม่ตรงแพ็กเกจ) โปรดติดต่อแอดมิน")
    else:
        await msg.edit_text(f"❌ **ทำรายการไม่ได้**\nเหตุผล: {res['message']}")

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
            app.add_handler(CallbackQueryHandler(button_click))
            async with app: await app.process_update(Update.de_json(update_data, app.bot))

        try: asyncio.run(main())
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop); loop.run_until_complete(main())
        except Exception as e: print(e)

        self.send_response(200); self.end_headers(); self.wfile.write(b'OK')
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"Bot OK")
