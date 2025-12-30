# ===========================================================
# ส่วน Server (แก้ใหม่: ให้ตะโกน Error ออกมา)
# ===========================================================
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_len = int(self.headers.get('Content-Length'))
        post_body = self.rfile.read(content_len)
        
        # ขั้นตอนที่ 1: แปลงข้อมูล
        try:
            json_string = post_body.decode('utf-8')
            update_data = json.loads(json_string)
            print(f"📩 ได้รับข้อความ: {json_string[:50]}...") # Log ให้รู้ว่ามีข้อความเข้า
        except Exception as e:
            print(f"❌ Error แปลง JSON: {e}")
            self.send_response(500)
            self.end_headers()
            return

        # ขั้นตอนที่ 2: รันบอท
        async def main():
            try:
                # เริ่มต้นแอปพลิเคชัน
                async with application:
                    update = Update.de_json(update_data, application.bot)
                    await application.process_update(update)
            except Exception as e:
                # ถ้าพังตรงนี้ ให้ปริ้นออกมา!
                print(f"❌ บอทพังขณะทำงาน (Runtime Error): {e}")

        try:
            # รัน Main Loop
            asyncio.run(main())
        except RuntimeError as e:
            # กรณี Loop ชนกัน (เจอบ่อยใน Vercel)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
        except Exception as e:
            print(f"❌ รัน Async ไม่ได้: {e}")

        # ส่งตอบกลับ 200 เสมอ (เพื่อไม่ให้ Telegram ส่งซ้ำ)
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running! (Debug Mode)")
