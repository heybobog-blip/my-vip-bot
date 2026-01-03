import os
import json
import asyncio
import re
import requests
import random
from datetime import datetime
import pytz 
import gspread 
from oauth2client.service_account import ServiceAccountCredentials 
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from http.server import BaseHTTPRequestHandler

# =================ตั้งค่าข้อมูลระบบ=================
TOKEN = os.environ.get("TELEGRAM_TOKEN")
ADMIN_GROUP_ID = -1003614142313 
MY_PHONE_NUMBER = "0659325591"  

# ชื่อไฟล์ Google Sheet
SHEET_NAME = "VVIP_Data" 

# =================ตั้งค่าห้อง=================
SELECTABLE_ROOMS = {
    "200": [
        {"id": -1003465527678, "name": "VVIP V1"},
        # {"id": IDห้องใหม่จากบอท @userinfobot, "name": "VVIP V2"},
    ],
    "400": [
        {"id": -1003477489997, "name": "VVIP V1 SAVE (400)"}
    ]
}

ALL_ACCESS_ROOMS = [
    {"id": -1003477489997, "name": "VVIP V1 SAVE"},
    # {"id": IDห้องใหม่จากบอท @userinfobot, "name": "VVIP V2"},
]

THANK_YOU_TEXT = "ขอบคุณที่ซัพพอร์ตครับ ฝากพิมพ์ +1 และ รีวิวในกลุ่มด้วยนะครับ ❤️"

# =========================================================
# ฟังก์ชันบันทึกลง Google Sheet
# =========================================================
def save_to_google_sheet(data_row):
    try:
        creds_json = os.environ.get("GOOGLE_CREDENTIALS")
        if not creds_json: return

        scope = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
                 "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]
        
        creds_dict = json.loads(creds_json)
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        
        sheet = client.open(SHEET_NAME).sheet1
        sheet.append_row(data_row)
        
    except Exception as e:
        print(f"Sheet Error: {e}")

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
                "full_name": full_name,
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
✨ ยินดีต้อนรับสู่... ✨
🔥 VVIP (เซียนจู เจริญPORN) 🔥
━━━━━━━━━━━━━━━━━━
💎 RATE PRICE (แพ็กเกจ) 💎

👑 999 บาท (ALL VVIP) 🔥🔥🔥
└ คุ้มที่สุด! จ่ายครั้งเดียวจบ เข้าได้ทุกกลุ่มยันชาติหน้า

🥈 400 บาท (VVIP SAVE)
└ สายเก็บ เซฟได้ไม่อั้น (กลุ่ม Save)

🥉 200 บาท (VVIP)
└ กลุ่มธรรมดา (ดูได้อย่างเดียว เซฟไม่ได้)
━━━━━━━━━━━━━━━━━━
🧧 ระบบจ่ายเงินอัตโนมัติ (Auto) 🧧
รวดเร็ว ไม่ต้องรอแอดมินตอบ!

📝 วิธีใช้งานบอทชำระเงิน
1. กดปุ่ม "จ่ายด้วยซอง TrueMoney"
2. อ่านวิธีทำซอง และสร้างลิงก์
3. ส่งลิงก์ซองเข้ามาในแชทนี้

❓ ติดปัญหา / มีคำถาม?
หากโอนเงินแล้วไม่ได้รับลิ้งค์ หรือต้องการสอบถามเพิ่มเติม
👉 กดปุ่ม "ซื้อกับแอดมิน" ด้านล่าง เพื่อติดต่อแอดมินโดยตรงครับ 👇
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

    # ลูกค้าเลือกห้องเอง (กรณีเงินตรงยอด)
    elif data.startswith("sel_"):
        try:
            _, gid, price = data.split('_')
            rnd = random.randint(1000,9999)
            link_name = f"User_{user_id}_{price}_{rnd}"
            link = await context.bot.create_chat_invite_link(chat_id=int(gid), member_limit=1, name=link_name)
            kb = [[InlineKeyboardButton("⭐️ กดเข้ากลุ่มที่นี่ ⭐️", url=link.invite_link)]]
            await query.edit_message_text(f"✅ **เลือกห้องเรียบร้อย**\nกดปุ่มด้านล่างเพื่อเข้าห้อง:\n(ลิ้งก์ใช้ได้ครั้งเดียว)", reply_markup=InlineKeyboardMarkup(kb))
            await context.bot.send_message(user_id, THANK_YOU_TEXT)
        except:
            await query.message.reply_text("❌ สร้างลิ้งก์ไม่สำเร็จ")

    # แอดมินกดอนุมัติ (กรณีเงินไม่ตรงยอด)
    elif data.startswith("apv_"):
        try:
            _, target_uid, room_price = data.split('_')
            target_uid = int(target_uid)
            rnd = random.randint(1000,9999)

            # สร้างลิ้งก์ให้ลูกค้า
            kb_client = []
            if room_price == "999":
                for g in ALL_ACCESS_ROOMS:
                    l = await context.bot.create_chat_invite_link(chat_id=g["id"], member_limit=1, name=f"AdminApv999_{target_uid}_{rnd}")
                    kb_client.append([InlineKeyboardButton(f"เข้า {g['name']}", url=l.invite_link)])
                await context.bot.send_message(target_uid, "✅ **แอดมินอนุมัติพิเศษให้แล้วครับ**\nกดเข้ากลุ่มด้านล่างได้เลย:", reply_markup=InlineKeyboardMarkup(kb_client))
            
            elif room_price in SELECTABLE_ROOMS:
                for r in SELECTABLE_ROOMS[room_price]:
                    kb_client.append([InlineKeyboardButton(f"เลือก {r['name']}", callback_data=f"sel_{r['id']}_{room_price}")])
                await context.bot.send_message(target_uid, f"✅ **แอดมินอนุมัติพิเศษให้แล้วครับ**\nเลือกห้องที่ต้องการ:", reply_markup=InlineKeyboardMarkup(kb_client))

            # แก้ข้อความในห้องแอดมิน
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ **อนุมัติเข้าห้อง {room_price} เรียบร้อย**")

        except Exception as e:
            await query.message.reply_text(f"❌ เกิดข้อผิดพลาด: {str(e)}")

async def handle_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    user = update.message.from_user
    msg = await update.message.reply_text("🤖 กำลังตรวจสอบซอง...")
    
    user_id = str(user.id)
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    username = f"@{user.username}" if user.username else "ไม่ระบุ"
    language = user.language_code or "ไม่ระบุ"
    is_premium = "Yes" if user.is_premium else "No"
    
    res = await asyncio.to_thread(redeem_truemoney, link, MY_PHONE_NUMBER)
    
    tz = pytz.timezone('Asia/Bangkok')
    now_str = datetime.now(tz).strftime('%d/%m/%Y %H:%M:%S')

    contact_btn = InlineKeyboardMarkup([[InlineKeyboardButton(f"💬 ติดต่อ: {first_name}", url=f"tg://user?id={user_id}")]])

    if res['status'] == 'success':
        amt = res['amount']
        sender_masked = res['sender_masked']
        full_name = res.get('full_name', 'ไม่ระบุ')
        v_hash = res.get('hash', 'N/A')
        
        sheet_data = [now_str, user_id, first_name, last_name, username, link, "สำเร็จ", amt, full_name, v_hash, language, is_premium]
        await asyncio.to_thread(save_to_google_sheet, sheet_data)
        
        # กรณีเงินตรงยอด (Auto)
        if str(amt) in SELECTABLE_ROOMS or amt >= 999:
            admin_report = f"""
🎁 **รายการสำเร็จ (Auto)**
🕒 {now_str}

💰 **ยอดเงิน: {amt} บาท**
👤 ทรูมันนี่: {sender_masked}
🎫 Hash: `{v_hash}`

👤 **ลูกค้า**
ชื่อ: {first_name} {last_name}
User: {username}
ID: `{user_id}`
"""
            try: await context.bot.send_message(ADMIN_GROUP_ID, admin_report, reply_markup=contact_btn, parse_mode='Markdown')
            except: pass
            
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
        
        # กรณีเงินไม่ตรงยอด (Manual Approve) --> เพิ่มส่วนนี้ให้ครับ
        else:
            admin_report = f"""
⚠️ **ยอดเงินไม่ตรงแพ็กเกจ**
🕒 {now_str}

💰 **ยอดที่ได้รับ: {amt} บาท**
(รับเงินเข้ากระเป๋าแล้ว แต่ยอดไม่ตรง 200/400/999)
👤 ทรูมันนี่: {sender_masked}
🎫 Hash: `{v_hash}`

👤 **ลูกค้า**
ชื่อ: {first_name} {last_name}
User: {username}
ID: `{user_id}`

👇 **กดปุ่มด้านล่างเพื่ออนุมัติห้อง:**
"""
            # สร้างปุ่มให้แอดมินเลือก
            admin_kb = [
                [InlineKeyboardButton("✅ ให้เข้าห้อง 200", callback_data=f"apv_{user_id}_200")],
                [InlineKeyboardButton("✅ ให้เข้าห้อง 400", callback_data=f"apv_{user_id}_400")],
                [InlineKeyboardButton("✅ ให้เข้าห้อง 999", callback_data=f"apv_{user_id}_999")],
                [InlineKeyboardButton(f"💬 ติดต่อลูกค้า", url=f"tg://user?id={user_id}")]
            ]
            try: await context.bot.send_message(ADMIN_GROUP_ID, admin_report, reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode='Markdown')
            except: pass

            await msg.edit_text(f"✅ **ได้รับยอด {amt} บาทแล้วครับ**\n⚠️ แต่ยอดเงินไม่ตรงกับแพ็กเกจ (200/400/999)\n\n⏳ **กรุณารอสักครู่ แอดมินกำลังตรวจสอบและส่งห้องให้ครับ...**")

    else:
        error_msg = res['message']
        sheet_data = [now_str, user_id, first_name, last_name, username, link, "ไม่สำเร็จ", 0, "-", error_msg, language, is_premium]
        await asyncio.to_thread(save_to_google_sheet, sheet_data)

        admin_warning = f"""
⚠️ **แจ้งเตือน: ซองใช้ไม่ได้/ซองเสีย**
🕒 {now_str}
🚫 **สาเหตุ:** {error_msg}
🔗 `{link}`
👤 {first_name} {last_name}
ID: `{user_id}`
"""
        try: await context.bot.send_message(ADMIN_GROUP_ID, admin_warning, reply_markup=contact_btn, parse_mode='Markdown')
        except: pass

        await msg.edit_text(f"❌ **ทำรายการไม่ได้**\nเหตุผล: {error_msg}")

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
