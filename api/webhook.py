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

# =================ตั้งค่าห้อง (ใส่เลข ID ให้ครบ)=================

# 1. ใส่เลข ID ห้องตรงนี้ครับ (อย่าลืมเครื่องหมายลบ -100)
ID_V1 = -1003465527678          # ห้อง V1
ID_SAVE = -1003477489997        # ห้อง SAVE
ID_ONLYFAN = -1003538823768     # <--- 🔴 แก้เลขนี้เป็น ID ห้อง ONLYFAN VIP ที่หามาครับ

# 2. ตั้งค่ากลุ่มสำหรับราคาที่ต้อง "เลือกอย่างใดอย่างหนึ่ง" (300, 500)
SELECTABLE_ROOMS = {
    "300": [
        {"id": ID_V1, "name": "VVIP V1"},
    ],
    "500": [
        {"id": ID_SAVE, "name": "VVIP V1 SAVE"},     # ทางเลือก 1
        {"id": ID_ONLYFAN, "name": "ONLYFAN VIP"}    # ทางเลือก 2
    ]
}

# 3. ตั้งค่ากลุ่มเหมา (999 และ 1299)
# ราคา 999 (ได้หมด ยกเว้น OnlyFan)
TIER_999_LIST = [
    # {"id": ID_V1, "name": "VVIP V1"},
    {"id": ID_SAVE, "name": "VVIP V1 SAVE"}
]

# ราคา 1299 (ได้ครบทุกอย่างรวม OnlyFan)
TIER_1299_LIST = [
    # {"id": ID_V1, "name": "VVIP V1"},
    {"id": ID_SAVE, "name": "VVIP V1 SAVE"},
    {"id": ID_ONLYFAN, "name": "ONLYFAN VIP"}
]

THANK_YOU_TEXT = "ขอบคุณที่ซัพพอร์ตครับ ฝากพิมพ์ +1 และ รีวิวในแชทแอดมินด้วยนะครับ ❤️"

# =========================================================
# ฟังก์ชันบันทึก Google Sheet
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
        try: data = response.json()
        except json.JSONDecodeError: return {"status": "error", "message": f"Server Error ({response.status_code})"}

        if data.get('status', {}).get('code') == 'SUCCESS':
            d = data.get('data', {})
            amt = float(d.get('my_ticket', {}).get('amount_baht', 0))
            full_name = d.get('owner_profile', {}).get('nickname', 'ไม่ระบุ')
            voucher_hash = d.get('voucher', {}).get('voucher_id', voucher_code) 
            name_parts = full_name.split()
            masked_name = f"{name_parts[0]} ***" if len(name_parts) > 1 else full_name
            
            return {
                "status": "success", "amount": int(amt), 
                "sender_masked": masked_name, "full_name": full_name, "hash": voucher_hash
            }
        else: return {"status": "error", "message": data.get('status', {}).get('code', 'Unknown Error')}
    except Exception as e: return {"status": "error", "message": str(e)}

# =========================================================
# ส่วนแสดงผล (Frontend)
# =========================================================

async def send_main_menu(update, context, is_edit=False):
    TEXT = """
✨ ยินดีต้อนรับสู่... ✨
🔥 <b>VVIP (เซียนจู เจริญPORN)</b> 🔥
━━━━━━━━━━━━━━━━━━
💎 <b>RATE PRICE (แพ็กเกจ)</b> 💎

👑 <b>1299 บาท (GOD TIER)</b> 🔥🔥🔥
└ <b>ได้ครบทุกกลุ่ม!</b> (กลุ่มหลัก + Save + ONLYFAN VIP)
└ จ่ายทีเดียวจบ ครบทุกอารมณ์

🏆 <b>999 บาท (KING TIER)</b>
└ ได้กลุ่มทุกกลุ่มของ VVIP + กลุ่ม Save (❌ ไม่รวม OnlyFan)

🥈 <b>500 บาท (เลือก 1 กลุ่ม)</b>
└ เลือกรับ: กลุ่ม Save <b>หรือ</b> ONLYFAN VIP

🥉 <b>300 บาท (VIP)</b>
└ กลุ่มธรรมดา (ดูได้อย่างเดียว)
━━━━━━━━━━━━━━━━━━
🧧 <b>ระบบจ่ายเงินอัตโนมัติ (Auto)</b> 🧧
รวดเร็ว ไม่ต้องรอแอดมินตอบ!

📝 <b>วิธีใช้งานบอทชำระเงิน</b>
1. กดปุ่ม "จ่ายด้วยซอง TrueMoney"
2. ใส่ยอดเงินตามแพ็กเกจ (300, 500, 999, 1299)
3. ส่งลิงก์ซองเข้ามาในแชทนี้

❓ ติดปัญหา / มีคำถาม?
👉 กดปุ่ม "ซื้อกับแอดมิน" ด้านล่าง 👇
"""
    keyboard = [
        [InlineKeyboardButton("🧧 จ่ายด้วยซอง TrueMoney (Auto 🚀)", callback_data="mode_gift")],
        [InlineKeyboardButton("👤 ซื้อกับแอดมิน 1", url="https://t.me/ZeinJu001"), InlineKeyboardButton("👤 ซื้อกับแอดมิน 2", url="https://t.me/duded16")],
        [InlineKeyboardButton("⭐️ เช็คเครดิต", url="https://t.me/+uoEnKbH_PP05NWQ1"), InlineKeyboardButton("🎥 กลุ่มตัวอย่าง", url="https://t.me/+5sWrRGBIm3Y5ODE1")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if is_edit:
        await update.callback_query.edit_message_text(text=TEXT, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text=TEXT, reply_markup=reply_markup, parse_mode='HTML')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update, context, is_edit=False)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "mode_gift":
        text = """
📝 <b>วิธีชำระเงินด้วยซองของขวัญ (ระบบออโต้)</b>
➖➖➖➖➖➖➖➖➖➖
1️⃣ เข้าแอป TrueMoney Wallet เลือกเมนู <b>'ซองของขวัญ'</b>
2️⃣ เลือกประเภท <b>'ส่งให้คนเดียว'</b>
3️⃣ ใส่ยอดเงินตามแพ็กเกจที่เลือก <b>(300, 500, 999, 1299)</b>
4️⃣ กดสร้างซอง > <b>คัดลอกลิ้งก์</b>

🚀 <b>นำลิ้งก์มาวางส่งในแชทนี้ได้เลยครับ ระบบจะดึงเข้ากลุ่มทันที</b>
"""
        kb = [[InlineKeyboardButton("🔙 กลับเมนูหลัก", callback_data="back_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

    elif data == "back_main":
        await send_main_menu(update, context, is_edit=True)

    # ลูกค้าเลือกห้องเอง (300, 500)
    elif data.startswith("sel_"):
        try:
            _, gid, price = data.split('_')
            rnd = random.randint(1000,9999)
            link_name = f"User_{user_id}_{price}_{rnd}"
            link = await context.bot.create_chat_invite_link(chat_id=int(gid), member_limit=1, name=link_name)
            kb = [[InlineKeyboardButton("⭐️ กดเข้ากลุ่มที่นี่ ⭐️", url=link.invite_link)]]
            await query.edit_message_text(f"✅ <b>เลือกห้องเรียบร้อย</b>\nกดปุ่มด้านล่างเพื่อเข้าห้อง:\n(ลิ้งก์ใช้ได้ครั้งเดียว)", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
            await context.bot.send_message(user_id, THANK_YOU_TEXT)
        except:
            await query.message.reply_text("❌ สร้างลิ้งก์ไม่สำเร็จ (โปรดแจ้งแอดมิน)")

    # แอดมินกดอนุมัติ (Manual Approve)
    elif data.startswith("apv_"):
        try:
            _, target_uid, room_price = data.split('_')
            target_uid = int(target_uid)
            rnd = random.randint(1000,9999)
            kb_client = []

            # สร้างลิ้งก์ตามราคาที่อนุมัติ
            if room_price == "1299":
                for g in TIER_1299_LIST:
                    l = await context.bot.create_chat_invite_link(chat_id=g["id"], member_limit=1, name=f"Apv1299_{target_uid}_{rnd}")
                    kb_client.append([InlineKeyboardButton(f"เข้า {g['name']}", url=l.invite_link)])
            
            elif room_price == "999":
                for g in TIER_999_LIST:
                    l = await context.bot.create_chat_invite_link(chat_id=g["id"], member_limit=1, name=f"Apv999_{target_uid}_{rnd}")
                    kb_client.append([InlineKeyboardButton(f"เข้า {g['name']}", url=l.invite_link)])
            
            elif room_price in SELECTABLE_ROOMS:
                for r in SELECTABLE_ROOMS[room_price]:
                    kb_client.append([InlineKeyboardButton(f"เลือก {r['name']}", callback_data=f"sel_{r['id']}_{room_price}")])

            await context.bot.send_message(target_uid, "✅ <b>แอดมินอนุมัติพิเศษให้แล้วครับ</b>\nกดเข้ากลุ่มด้านล่างได้เลย:", reply_markup=InlineKeyboardMarkup(kb_client), parse_mode='HTML')
            await query.edit_message_caption(caption=f"{query.message.caption}\n\n✅ <b>อนุมัติเข้าห้อง {room_price} เรียบร้อย</b>", parse_mode='HTML')

        except Exception as e:
            await query.message.reply_text(f"❌ เกิดข้อผิดพลาด: {str(e)}")

async def handle_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    user = update.message.from_user
    msg = await update.message.reply_text("🤖 กำลังตรวจสอบซอง...")
    
    # เก็บข้อมูลลูกค้า (รวมชื่อ-นามสกุล)
    user_id = str(user.id)
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    full_tg_name = f"{first_name} {last_name}".strip() # รวมชื่อนามสกุล
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
        
        # บันทึกลง Sheet (รวมชื่อแล้ว)
        sheet_data = [now_str, user_id, full_tg_name, username, link, "สำเร็จ", amt, full_name, v_hash, language, is_premium]
        await asyncio.to_thread(save_to_google_sheet, sheet_data)
        
        # ตรวจสอบยอดเงิน (เพิ่ม 1299)
        if str(amt) in SELECTABLE_ROOMS or amt >= 999:
            admin_report = f"""
🎁 <b>รายการสำเร็จ (Auto)</b>
🕒 {now_str}

💰 <b>ยอดเงิน: {amt} บาท</b>
👤 ทรูมันนี่: {sender_masked}
🎫 Hash: <code>{v_hash}</code>

👤 <b>ลูกค้า</b>
ชื่อ: {full_tg_name}
User: {username}
ID: <code>{user_id}</code>
"""
            try: await context.bot.send_message(ADMIN_GROUP_ID, admin_report, reply_markup=contact_btn, parse_mode='HTML')
            except Exception as e: print(f"❌ Send Admin Error: {e}")
            
            rnd = random.randint(1000,9999)
            
            # กรณี 1299 (ได้ครบทุกอย่าง)
            if amt >= 1299:
                kb = []
                for g in TIER_1299_LIST:
                    l = await context.bot.create_chat_invite_link(chat_id=g["id"], member_limit=1, name=f"Auto1299_{user.id}_{rnd}")
                    kb.append([InlineKeyboardButton(f"เข้า {g['name']}", url=l.invite_link)])
                await msg.edit_text(f"✅ <b>ได้รับยอด {amt} บาท (GOD TIER)</b>\nกดเข้ากลุ่มด้านล่าง:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

            # กรณี 999 (ได้ V1+SAVE)
            elif amt >= 999:
                kb = []
                for g in TIER_999_LIST:
                    l = await context.bot.create_chat_invite_link(chat_id=g["id"], member_limit=1, name=f"Auto999_{user.id}_{rnd}")
                    kb.append([InlineKeyboardButton(f"เข้า {g['name']}", url=l.invite_link)])
                await msg.edit_text(f"✅ <b>ได้รับยอด {amt} บาท (KING TIER)</b>\nกดเข้ากลุ่มด้านล่าง:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
            
            # กรณี 300, 500 (เลือกห้อง)
            elif str(amt) in SELECTABLE_ROOMS:
                kb = []
                for r in SELECTABLE_ROOMS[str(amt)]:
                    kb.append([InlineKeyboardButton(f"เลือก {r['name']}", callback_data=f"sel_{r['id']}_{amt}")])
                await msg.edit_text(f"✅ <b>ได้รับยอด {amt} บาท</b>\nเลือกห้องที่ต้องการ:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
        
        # ยอดไม่ตรง (Manual Approve)
        else:
            admin_report = f"""
⚠️ <b>ยอดเงินไม่ตรงแพ็กเกจ</b>
🕒 {now_str}
💰 <b>ยอดที่ได้รับ: {amt} บาท</b>
(รับเงินแล้ว แต่ยอดไม่ตรง 300/500/999/1299)
👤 ทรูมันนี่: {sender_masked}
🎫 Hash: <code>{v_hash}</code>
👤 <b>ลูกค้า:</b> {full_tg_name}
"""
            admin_kb = [
                [InlineKeyboardButton("✅ เข้า 300", callback_data=f"apv_{user_id}_300"), InlineKeyboardButton("✅ เข้า 500", callback_data=f"apv_{user_id}_500")],
                [InlineKeyboardButton("✅ เข้า 999", callback_data=f"apv_{user_id}_999"), InlineKeyboardButton("✅ เข้า 1299", callback_data=f"apv_{user_id}_1299")],
                [InlineKeyboardButton(f"💬 ติดต่อลูกค้า", url=f"tg://user?id={user_id}")]
            ]
            try: await context.bot.send_message(ADMIN_GROUP_ID, admin_report, reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode='HTML')
            except: pass
            await msg.edit_text(f"✅ <b>ได้รับยอด {amt} บาทแล้วครับ</b>\n⚠️ ยอดเงินไม่ตรงแพ็กเกจ รอแอดมินตรวจสอบสักครู่ครับ...", parse_mode='HTML')

    # กรณีซองเสีย
    else:
        error_msg = res['message']
        sheet_data = [now_str, user_id, full_tg_name, username, link, "ไม่สำเร็จ", 0, "-", error_msg, language, is_premium]
        await asyncio.to_thread(save_to_google_sheet, sheet_data)

        admin_warning = f"""
⚠️ <b>แจ้งเตือน: ซองใช้ไม่ได้/ซองเสีย</b>
🕒 {now_str}
🚫 <b>สาเหตุ:</b> {error_msg}
🔗 <code>{link}</code>
👤 <b>คนส่ง:</b> {full_tg_name}
"""
        try: await context.bot.send_message(ADMIN_GROUP_ID, admin_warning, reply_markup=contact_btn, parse_mode='HTML')
        except: pass
        await msg.edit_text(f"❌ <b>ทำรายการไม่ได้</b>\nเหตุผล: {error_msg}", parse_mode='HTML')

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
