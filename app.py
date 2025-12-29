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
import time
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Cấu hình lấy từ Environment Variables trên Render
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'my_secret_token_123')

def send_message(recipient_id, message_text):
    if not PAGE_ACCESS_TOKEN:
        app.logger.error("LỖI: Chưa có PAGE_ACCESS_TOKEN!")
        return
        
    url = f"https://graph.facebook.com/v20.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    headers = {'Content-Type': 'application/json'}
    data = {'recipient': {'id': recipient_id}, 'message': {'text': message_text}}
    requests.post(url, headers=headers, json=data)

def perform_unlock(ff_id, recipient_id):
    driver = None
    try:
        # Cấu hình trình duyệt SIÊU NHẸ để tránh lỗi RAM trên Render Free
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-extensions')
        options.add_argument('--blink-settings=imagesEnabled=false') # Tắt tải ảnh để tiết kiệm RAM
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30) 
        driver.get('https://unlockffbeta.com/')
        
        wait = WebDriverWait(driver, 35)
        
        # Nhập ID bằng JavaScript (Sửa lỗi invalid element state)
        id_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input")))
        driver.execute_script("arguments[0].value = arguments[1];", id_input, ff_id)
        
        # Click nút Unlock
        unlock_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Unlock')]")))
        driver.execute_script("arguments[0].click();", unlock_btn)
        
        try:
            # Đợi kết quả 100% (Tối đa 45 giây)
            wait.until(EC.text_to_be_present_in_element((By.XPATH, "//body"), "100%"), timeout=45)
            
            # Giao diện tin nhắn Thành công (Đã Custom đẹp)
            msg = (
                "┏━━━━━━━━━━━━━━━┓\n"
                "     🔓 UNLOCK SUCCESS\n"
                "┗━━━━━━━━━━━━━━━┛\n\n"
                f"👤 ID Nhân vật: {ff_id}\n"
                "⏳ Trạng thái: Đã mở khóa (2 Giờ)\n"
                "🚀 Loại: Bypass Beta (Non-Discord)\n\n"
                "👉 Hết hạn hãy gửi lại lệnh để Renew.\n"
                "⚠️ Khuyên dùng acc phụ để trải nghiệm!"
            )
        except TimeoutException:
            # Giao diện tin nhắn Thất bại/Không tồn tại
            msg = (
                "┏━━━━━━━━━━━━━━━┓\n"
                "      ❌ UNLOCK FAILED\n"
                "┗━━━━━━━━━━━━━━━┛\n\n"
                f"👤 ID: {ff_id}\n"
                "❓ Lý do: UID không tồn tại hoặc web lỗi.\n\n"
                "💡 Vui lòng kiểm tra lại ID của bạn!"
            )
        
        send_message(recipient_id, msg)
        
    except Exception as e:
        app.logger.error(f"Lỗi Selenium: {str(e)}")
        send_message(recipient_id, "⚠️ Hệ thống đang quá tải hoặc Web gốc bị chặn. Thử lại sau 1 phút!")
    finally:
        if driver:
            driver.quit()

@app.route('/', methods=['GET'])
def verify():
    if request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge'), 200
    return "Bot FF Beta Online!", 200

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
                        # Tin nhắn chờ đẹp mắt
                        send_message(sender_id, f"🔄 Đang xử lý ID: {ff_id}\n━━━━━━━━━━━━━━\n⌛ Vui lòng chờ khoảng 45-60 giây...")
                        threading.Thread(target=perform_unlock, args=(ff_id, sender_id)).start()
                    else:
                        send_message(sender_id, "👋 Chào bro! Tôi là Bot Unlock FF.\n\nĐể mở khóa Beta, hãy gửi:\n📝 /unlock [Số ID]\n\nVí dụ: /unlock 12345678")
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
