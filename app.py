from flask import Flask, request, abort
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

# Lấy thông tin từ Environment Variables trên Render để bảo mật
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN')
GRAPH_API_URL = 'https://graph.facebook.com/v20.0/me/messages'

def send_message(recipient_id, message_text):
    if not PAGE_ACCESS_TOKEN:
        app.logger.error("PAGE_ACCESS_TOKEN chưa được thiết lập!")
        return
        
    params = {'access_token': PAGE_ACCESS_TOKEN}
    headers = {'Content-Type': 'application/json'}
    data = {
        'recipient': {'id': recipient_id},
        'message': {'text': message_text}
    }
    response = requests.post(GRAPH_API_URL, params=params, headers=headers, json=data)
    if response.status_code != 200:
        app.logger.error(f"Gửi tin nhắn thất bại: {response.text}")

def perform_unlock(ff_id, recipient_id):
    driver = None
    try:
        options = Options()
        # Các tùy chọn bắt buộc để chạy Selenium trên Server Render
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        
        # Khởi tạo driver (Render sẽ tự nhận diện chrome đã cài qua build script)
        driver = webdriver.Chrome(options=options)
        driver.get('https://unlockffbeta.com/')
        
        wait = WebDriverWait(driver, 45)
        
        # Tìm input UID
        id_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input")))
        id_input.clear()
        id_input.send_keys(ff_id)
        
        # Nhấn nút Unlock
        unlock_btn = wait.until(EC.element_to_be_clickable((By.XPATH, 
            "//button[contains(text(), 'Unlock without Discord') or contains(text(), 'Unlock for 2 Hours')]")))
        unlock_btn.click()
        
        # Đợi xử lý đến khi thấy 100%
        try:
            wait.until(EC.text_to_be_present_in_element((By.XPATH, "//body"), "100%"), timeout=60)
            result = f"✅ Unlock thành công ID {ff_id}!\n\nĐã mở khóa tạm thời **2 giờ**.\nHết hạn hãy gửi lại lệnh nhé bro! 🚀"
        except TimeoutException:
            result = f"❌ Unlock thất bại ID {ff_id}!\n\nID không tồn tại hoặc hệ thống web bận. Hãy thử UID khác!"
        
        send_message(recipient_id, result)
        
    except Exception as e:
        app.logger.error(f"Lỗi Selenium: {str(e)}")
        send_message(recipient_id, f"❌ Có lỗi xảy ra khi xử lý ID {ff_id}. Thử lại sau ít phút!")
    finally:
        if driver:
            driver.quit() # Giải phóng RAM cho Render

@app.route('/', methods=['GET'])
def verify():
    # Facebook dùng GET để xác thực Webhook
    if request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge')
    return "Sai Verify Token", 403

@app.route('/', methods=['POST'])
def webhook():
    # Facebook dùng POST để gửi dữ liệu tin nhắn
    data = request.get_json()
    if data.get('object') == 'page':
        for entry in data['entry']:
            for messaging in entry.get('messaging', []):
                sender_id = messaging['sender']['id']
                if 'message' in messaging and 'text' in messaging['message']:
                    message_text = messaging['message']['text'].strip()
                    
                    # Kiểm tra cú pháp /unlock [UID]
                    match = re.match(r'^/unlock\s+(\d{8,11})$', message_text, re.IGNORECASE)
                    if match:
                        ff_id = match.group(1)
                        send_message(sender_id, f"🔄 Đang check & unlock ID {ff_id}... Vui lòng đợi trong giây lát!")
                        # Chạy Selenium trong luồng riêng để không làm Webhook bị timeout
                        threading.Thread(target=perform_unlock, args=(ff_id, sender_id)).start()
                    else:
                        send_message(sender_id, "Sai cú pháp rồi!\nHãy gửi: /unlock [UID]\nVí dụ: /unlock 12345678")
    return "OK", 200

if __name__ == '__main__':
    # Render yêu cầu dùng port từ biến môi trường PORT
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)