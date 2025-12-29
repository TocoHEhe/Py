from flask import Flask, request
import requests
import re
import threading
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.chrome.options import Options
import os
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Lấy cấu hình từ Environment Variables
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'tocolate1104')

def send_message(recipient_id, message_text):
    if not PAGE_ACCESS_TOKEN:
        app.logger.error("LỖI: Thiếu Token trong Environment!")
        return
    url = f"https://graph.facebook.com/v20.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    headers = {'Content-Type': 'application/json'}
    data = {'recipient': {'id': recipient_id}, 'message': {'text': message_text}}
    requests.post(url, headers=headers, json=data)

def perform_unlock(ff_id, recipient_id):
    driver = None
    try:
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--blink-settings=imagesEnabled=false') # Tắt ảnh giúp load web cực nhanh
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        driver.get('https://unlockffbeta.com/')
        
        wait = WebDriverWait(driver, 35)
        
        # Nhập UID bằng JavaScript (Tránh lỗi invalid element state)
        id_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input")))
        driver.execute_script("arguments[0].value = arguments[1];", id_input, ff_id)
        
        # Click nút Unlock
        unlock_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Unlock')]")))
        driver.execute_script("arguments[0].click();", unlock_btn)
        
        try:
            # Đợi kết quả 100%
            wait.until(EC.text_to_be_present_in_element((By.XPATH, "//body"), "100%"), timeout=45)
            
            # GIAO DIỆN THÀNH CÔNG RỰC RỠ
            msg = (
                "╔══════════════╗\n"
                "       🔓 UNLOCK THÀNH CÔNG\n"
                "╚══════════════╝\n\n"
                f"👤 ID: {ff_id}\n"
                "✨ Trạng thái: Đã mở khóa thành công\n"
                "⏰ Thời gian: Tạm thời 2 giờ\n"
                "🚀 Hệ thống: Bypass Beta High Speed\n\n"
                "━━━━━━━━━━━━━━━\n"
                "👉 Hãy đăng nhập và chiến ngay bro!\n"
                "⚠️ Lưu ý: Nên dùng acc phụ để test."
            )
        except TimeoutException:
            # GIAO DIỆN THẤT BẠI
            msg = (
                "╔══════════════╗\n"
                "      ❌ UNLOCK THẤT BẠI\n"
                "╚══════════════╝\n\n"
                f"👤 ID: {ff_id}\n"
                "❓ Lý do: ID không tồn tại hoặc sai UID.\n\n"
                "💡 Vui lòng kiểm tra lại dãy số ID!"
            )
        
        send_message(recipient_id, msg)
        
    except Exception as e:
        app.logger.error(f"Lỗi Selenium: {str(e)}")
        send_message(recipient_id, "⚠️ Hệ thống đang quá tải. Thử lại sau 1 phút nhé!")
    finally:
        if driver:
            driver.quit()

@app.route('/', methods=['GET'])
def verify():
    if request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge'), 200
    return "Bot FF Beta - Online & Ready! 🚀", 200

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if data.get('object') == 'page':
        for entry in data['entry']:
            for messaging in entry.get('messaging', []):
                sender_id = messaging['sender']['id']
                if 'message' in messaging and 'text' in messaging['message']:
                    text = messaging['message']['text'].strip()
                    match = re.match(r'^/unlock\s+(\d+)$', text, re.IGNORECASE)
                    if match:
                        ff_id = match.group(1)
                        # TIN NHẮN CHỜ MÀU MÈ
                        processing_msg = (
                            f"🔄 Đang xử lý ID: {ff_id}\n"
                            "━━━━━━━━━━━━━━━\n"
                            "⏳ Hệ thống đang mở khóa...\n"
                            "⌛ Vui lòng chờ khoảng 45-60 giây!"
                        )
                        send_message(sender_id, processing_msg)
                        threading.Thread(target=perform_unlock, args=(ff_id, sender_id)).start()
                    else:
                        # HƯỚNG DẪN CÚ PHÁP
                        help_msg = (
                            "👋 Chào bro! Tôi là Bot Unlock FF.\n\n"
                            "Để sử dụng, hãy gửi lệnh:\n"
                            "📝 /unlock [Số UID của bạn]\n\n"
                            "Ví dụ: /unlock 12345678\n"
                            "━━━━━━━━━━━━━━━\n"
                            "⚡ Hệ thống chạy hoàn toàn tự động!"
                        )
                        send_message(sender_id, help_msg)
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

