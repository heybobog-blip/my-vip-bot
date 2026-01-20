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
ID_V1 = -1003465527678
ID_SAVE = -1003477489997
ID_ONLYFAN = -1003413682717
ID_MONTHLY = -1003592949127
ID_INTER = -1003357989161
ID_SERIES = -1003281870942

# ราคา 300, 500
SELECTABLE_ROOMS = {
    "300": [
        {"id": ID_V1, "name": "VVIP V1"}
    ],
    "500": [
        {"id": ID_SAVE, "name": "VVIP V1 SAVE"},
        {"id": ID_ONLYFAN, "name": "ONLYFAN VIP"}
    ]
}

# ราคา 999
TIER_999_LIST = [
    {"id": ID_SAVE, "name": "VVIP V1 SAVE"},
    {"id": ID_MONTHLY, "name": "VVIP (ถาวร)"}
]

# ราคา 1299
TIER_1299_LIST = [
    {"id": ID_SAVE, "name": "VVIP V1 SAVE"},
    {"id": ID_ONLYFAN, "name": "ONLYFAN VIP"},
    {"id": ID_MONTHLY, "name": "VVIP (ถาวร)"},
    {"id": ID_INTER, "name": "VVIP นานาชาติ"},
    {"id": ID_SERIES, "name": "หนังพรีเมี่ยม"}
]

THANK_YOU_TEXT = "ขอบคุณที่ซัพพอร์ตครับ ฝากพิมพ์ +1 และ รีวิวในแชทแอดมินด้วยนะครับ Enjoy❤️"

# ================= ฟังก์ชันบันทึก Sheet =================
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

# ================= ฟังก์ชันเช็คซอง =================
def redeem_truemoney(url, phone_number):
    try:
        match = re.search(r'v=([a-zA-Z0-9]+)', url)
        if not match: return {"status": "error", "message": "ลิ้งก์ผิดรูปแบบ"}
        voucher_code = match.group(1)
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36',
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
        except: return {"status": "error", "message": f"Server Error ({response.status_code})"}

        if data.get('status', {}).get('code') == 'SUCCESS':
            d = data.get('data', {})
            amount_str = d.get('my_ticket', {}).get('amount_baht', '0').replace(',', '')
            amt = float(amount_str)
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

# ================= ส่วน Frontend =================
async def send_main_menu(update, context, is_edit=False):
    TEXT = """
✨ ยินดีต้อนรับสู่... ✨
🔥 <b>VVIP (เซียนจู เจริญพร)</b> 🔥
━━━━━━━━━━━━━━━━━━
💎 <b>RATE PRICE (แพ็กเกจ)</b> 💎

👑 <b>1299 บาท (GOD TIER)</b> 🔥🔥🔥
└ <b>ได้ครบทุกกลุ่ม!</b>
└ กลุ่ม VVIP (ถาวร)
└ กลุ่มเซฟคลิปได้
└ ONLYFAN VIP
└ VVIP นานาชาติ
└ หนังพรีเมี่ยม ไทย/จีน/เกาหลี
└ จ่ายทีเดียวจบ ครบทุกอารมณ์

🏆 <b>999 บาท (KING TIER)</b>
└ ได้กลุ่ม VVIP (ถาวร) + กลุ่มSave
└ ❌ ไม่รวม OnlyFan และ VVIP นานาชาติ

🥈 <b>500 บาท (เลือก 1 กลุ่ม)</b>
└ เลือกรับ: กลุ่มเซฟคลิปได้ <b>หรือ</b> ONLYFAN VIP

🥉 <b>300 บาท (เลือก 1 กลุ่ม)</b>
└ เลือกรับ: VVIP V1 ถาวร(อัพคลิปถึง 22/01/69)
━━━━━━━━━━━━━━━━━━
🧧 <b>ระบบจ่ายเงินอัตโนมัติ (Auto)</b> 🧧
รวดเร็ว ไม่ต้องรอแอดมินตอบ!

📝 <b>วิธีใช้งานบอทชำระเงิน</b>
1. กดปุ่ม "จ่ายด้วยซอง TrueMoney"
2. ใส่ยอดเงินตามแพ็กเกจ (300, 500, 999, 1299)
3. ส่งลิงก์ซองเข้ามาในแชทนี้

❓ ติดปัญหา / มีคำถาม?
👉 กดปุ่ม "👤 ติดต่อแอดมิน" ด้านล่าง 👇
"""
    keyboard = [
        [InlineKeyboardButton("🧧 จ่ายด้วยซอง TrueMoney (Auto 🚀)", callback_data="mode_gift")],
        [InlineKeyboardButton("⭐️ เช็คเครดิต", url="https://t.me/+uoEnKbH_PP05NWQ1"), InlineKeyboardButton("🎥 กลุ่มตัวอย่าง", url="https://t.me/+5sWrRGBIm3Y5ODE1")],
        [InlineKeyboardButton("👤 ติดต่อแอดมิน 1", url="https://t.me/ZeinJu001"), InlineKeyboardButton("👤 ติดต่อแอดมิน 2", url="https://t.me/duded16")]
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
        HOW_TO_IMG = "https://img5.pic.in.th/file/secure-sv1/photo_2026-01-07_05-30-56-copy.jpg"
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
        await query.message.delete()
        await context.bot.send_photo(chat_id=user_id, photo=HOW_TO_IMG, caption=text, reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

    elif data == "back_main":
        await query.message.delete()
        await send_main_menu(update, context, is_edit=False)

    elif data.startswith("sel_"):
        try:
            _, gid, price = data.split('_')
            rnd = random.randint(1000,9999)
            link_name = f"User_{user_id}_{price}_{rnd}"
            link = await context.bot.create_chat_invite_link(chat_id=int(gid), member_limit=1, name=link_name)
            kb = [[InlineKeyboardButton("⭐️ กดเข้ากลุ่มที่นี่ ⭐️", url=link.invite_link)]]
            await query.edit_message_text(f"✅ <b>เลือกห้องเรียบร้อย</b>\nกดปุ่มด้านล่างเพื่อเข้าห้อง:\n(ลิ้งก์ใช้ได้ครั้งเดียว)", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
            await context.bot.send_message(user_id, THANK_YOU_TEXT)
        except Exception as e:
            await query.message.reply_text(f"❌ Error: {e}")

    # ================= ส่วนอนุมัติ =================
    elif data.startswith("apv_"):
        try:
            _, target_uid, room_price = data.split('_')
            target_uid = int(target_uid)
            rnd = random.randint(1000,9999)
            kb_client = []
            error_logs = []

            target_list = []
            if room_price == "1299": target_list = TIER_1299_LIST
            elif room_price == "999": target_list = TIER_999_LIST
            elif room_price in SELECTABLE_ROOMS: target_list = SELECTABLE_ROOMS[room_price]

            for g in target_list:
                try:
                    l = await context.bot.create_chat_invite_link(chat_id=g["id"], member_limit=1, name=f"Apv{room_price}_{target_uid}_{rnd}")
                    action_text = f"เข้า {g['name']}" if room_price not in ["300", "500"] else f"เลือก {g['name']}"
                    callback = l.invite_link if room_price not in ["300", "500"] else f"sel_{g['id']}_{room_price}"
                    
                    if room_price in ["300", "500"]:
                        kb_client.append([InlineKeyboardButton(action_text, callback_data=callback)])
                    else:
                        kb_client.append([InlineKeyboardButton(action_text, url=callback)])
                except Exception as e:
                    error_logs.append(f"- {g['name']}: {e}")

            if kb_client:
                try:
                    await context.bot.send_message(target_uid, "✅ <b>สลิป/ยอดเงิน ได้รับการอนุมัติแล้วครับ</b>\nกดเข้ากลุ่มด้านล่างได้เลย:", reply_markup=InlineKeyboardMarkup(kb_client), parse_mode='HTML')
                    
                    msg_status = f"✅ <b>อนุมัติเข้าห้อง {room_price} เรียบร้อย</b>"
                    if error_logs: msg_status += "\n\n⚠️ <b>พบปัญหาบางห้อง:</b>\n" + "\n".join(error_logs)

                    original_text = query.message.caption if query.message.caption else query.message.text
                    try: await query.edit_message_caption(caption=f"{original_text}\n\n{msg_status}", parse_mode='HTML')
                    except: await query.edit_message_text(text=f"{original_text}\n\n{msg_status}", parse_mode='HTML')

                    # 🔴 บันทึกลง Google Sheet
                    try:
                        user_info = await context.bot.get_chat(target_uid)
                        full_name = f"{user_info.first_name or ''} {user_info.last_name or ''}".strip()
                        username = f"@{user_info.username}" if user_info.username else "ไม่ระบุ"
                        tz = pytz.timezone('Asia/Bangkok')
                        now_str = datetime.now(tz).strftime('%d/%m/%Y %H:%M:%S')

                        sheet_data = [
                            now_str, str(target_uid), full_name, username, "สลิปโอนเงิน (Manual)", "สำเร็จ",
                            int(room_price), "Admin Approved", "Slip Verification", "-", "-"
                        ]
                        await asyncio.to_thread(save_to_google_sheet, sheet_data)
                    except Exception as e:
                        print(f"❌ Save Sheet Error: {e}")

                except Exception as e:
                    await query.message.reply_text(f"❌ ส่งหาลูกค้าไม่สำเร็จ (เขาบล็อกบอท?): {e}")
            else:
                await query.message.reply_text(f"❌ สร้างลิ้งก์ไม่ได้เลย: {error_logs}")

        except Exception as e:
            await query.message.reply_text(f"❌ Error: {str(e)}")

    # ปุ่มปฏิเสธสลิป
    elif data.startswith("reject_"):
        _, target_uid = data.split('_')
        try:
            contact_kb = [
                [InlineKeyboardButton("👤 ติดต่อแอดมิน 1", url="https://t.me/ZeinJu001")],
                [InlineKeyboardButton("👤 ติดต่อแอดมิน 2", url="https://t.me/duded16")]
            ]

            await context.bot.send_message(
                chat_id=target_uid, 
                text="❌ <b>สลิปไม่ผ่านการตรวจสอบ</b>\nโปรดติดต่อแอดมินเพื่อสอบถามข้อมูลเพิ่มเติม", 
                reply_markup=InlineKeyboardMarkup(contact_kb),
                parse_mode='HTML'
            )
            
            original_text = query.message.caption if query.message.caption else query.message.text
            try: await query.edit_message_caption(caption=f"{original_text}\n\n❌ <b>ปฏิเสธแล้ว</b>", parse_mode='HTML')
            except: await query.edit_message_text(text=f"{original_text}\n\n❌ <b>ปฏิเสธแล้ว</b>", parse_mode='HTML')
        except:
            await query.message.reply_text("❌ ส่งแจ้งเตือนลูกค้าไม่ได้")

# ================= ฟังก์ชันรับรูปสลิป =================
async def handle_slip_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # เช็คว่าเป็นการคุยส่วนตัวเท่านั้น
    if update.message.chat.type != 'private':
        return

    if not update.message.photo: return
    
    photo_file = update.message.photo[-1].file_id
    user = update.message.from_user
    user_id = user.id
    name = user.first_name
    username = f"@{user.username}" if user.username else "ไม่ระบุ"

    admin_caption = f"""
🧾 <b>ได้รับสลิปใหม่!</b>
👤 <b>ลูกค้า:</b> {name} ({username})
🆔 <code>{user_id}</code>

👇 <b>กดปุ่มด้านล่างเพื่ออนุมัติและส่งลิ้งก์:</b>
"""
    # 🔴 เพิ่มปุ่มติดต่อลูกค้าตรงนี้ครับ
    kb = [
        [InlineKeyboardButton("✅ อนุมัติ 300", callback_data=f"apv_{user_id}_300"), InlineKeyboardButton("✅ อนุมัติ 500", callback_data=f"apv_{user_id}_500")],
        [InlineKeyboardButton("✅ อนุมัติ 999", callback_data=f"apv_{user_id}_999"), InlineKeyboardButton("✅ อนุมัติ 1299", callback_data=f"apv_{user_id}_1299")],
        [InlineKeyboardButton("❌ ปฏิเสธสลิป", callback_data=f"reject_{user_id}")],
        [InlineKeyboardButton(f"💬 ติดต่อลูกค้า ({name})", url=f"tg://user?id={user_id}")]
    ]

    try:
        await context.bot.send_photo(
            chat_id=ADMIN_GROUP_ID,
            photo=photo_file,
            caption=admin_caption,
            reply_markup=InlineKeyboardMarkup(kb),
            parse_mode='HTML'
        )
        await update.message.reply_text("📨 <b>ได้รับสลิปแล้วครับ</b>\nรอแอดมินตรวจสอบสักครู่ ระบบจะส่งลิ้งก์ให้ทันทีเมื่ออนุมัติครับ", parse_mode='HTML')
    except Exception as e:
        await update.message.reply_text(f"❌ เกิดข้อผิดพลาดในการส่งสลิป: {e}")

async def handle_gift(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = update.message.text.strip()
    user = update.message.from_user
    msg = await update.message.reply_text("🤖 กำลังตรวจสอบซอง...")
    user_id = str(user.id)
    first_name = user.first_name or ""
    last_name = user.last_name or ""
    full_tg_name = f"{first_name} {last_name}".strip()
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
        sheet_data = [now_str, user_id, full_tg_name, username, link, "สำเร็จ", amt, full_name, v_hash, language, is_premium]
        await asyncio.to_thread(save_to_google_sheet, sheet_data)

        if str(amt) in SELECTABLE_ROOMS or amt >= 999:
            admin_report = f"""
🎁 <b>รายการสำเร็จ (Auto)</b>
🕒 {now_str}
💰 <b>ยอดเงิน: {amt} บาท</b>
👤 ทรูมันนี่: {sender_masked}
🎫 Hash: <code>{v_hash}</code>
👤 <b>ลูกค้า:</b> {full_tg_name} (ID: {user_id})
"""
            try: await context.bot.send_message(ADMIN_GROUP_ID, admin_report, reply_markup=contact_btn, parse_mode='HTML')
            except: pass

            rnd = random.randint(1000,9999)
            kb = []
            target_list = []
            if amt >= 1299: target_list = TIER_1299_LIST
            elif amt >= 999: target_list = TIER_999_LIST
            
            if target_list:
                for g in target_list:
                    try:
                        l = await context.bot.create_chat_invite_link(chat_id=g["id"], member_limit=1, name=f"Auto{int(amt)}_{user.id}_{rnd}")
                        kb.append([InlineKeyboardButton(f"เข้า {g['name']}", url=l.invite_link)])
                    except Exception as e:
                        print(f"Error creating link for {g['id']}: {e}")
                
                tier_name = "GOD TIER" if amt >= 1299 else "KING TIER"
                await msg.edit_text(f"✅ <b>ได้รับยอด {amt} บาท ({tier_name})</b>\nกดเข้ากลุ่มด้านล่าง:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')
            
            elif str(amt) in SELECTABLE_ROOMS:
                for r in SELECTABLE_ROOMS[str(amt)]:
                    kb.append([InlineKeyboardButton(f"เลือก {r['name']}", callback_data=f"sel_{r['id']}_{amt}")])
                await msg.edit_text(f"✅ <b>ได้รับยอด {amt} บาท</b>\nเลือกห้องที่ต้องการ:", reply_markup=InlineKeyboardMarkup(kb), parse_mode='HTML')

        else:
            admin_report = f"""
⚠️ <b>ยอดเงินไม่ตรงแพ็กเกจ</b>
🕒 {now_str}
💰 <b>ยอดที่ได้รับ: {amt} บาท</b>
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
    else:
        error_msg = res['message']
        sheet_data = [now_str, user_id, full_tg_name, username, link, "ไม่สำเร็จ", 0, "-", error_msg, language, is_premium]
        await asyncio.to_thread(save_to_google_sheet, sheet_data)
        admin_warning = f"""
⚠️ <b>แจ้งเตือน: ซองเสีย/ใช้ไม่ได้</b>
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
            app.add_handler(MessageHandler(filters.PHOTO, handle_slip_image))
            app.add_handler(CallbackQueryHandler(button_click))
            async with app: await app.process_update(Update.de_json(update_data, app.bot))

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running(): loop.create_task(main())
            else: loop.run_until_complete(main())
        except RuntimeError: asyncio.run(main())
        except: pass

        self.send_response(200); self.end_headers(); self.wfile.write(b'OK')
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"Bot OK")
