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
