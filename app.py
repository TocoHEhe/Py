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

# --- THÔNG TIN CẤU HÌNH ---
# Lấy từ Environment Variables trên Render
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'my_secret_token_123')
GRAPH_API_URL = 'https://graph.facebook.com/v20.0/me/messages'

def send_message(recipient_id, message_text):
    if not PAGE_ACCESS_TOKEN:
        app.logger.error("LỖI: Chưa có PAGE_ACCESS_TOKEN trong Environment Variables!")
        return
        
    params = {'access_token': PAGE_ACCESS_TOKEN}
    headers = {'Content-Type': 'application/json'}
    data = {
        'recipient': {'id': recipient_id},
        'message': {'text': message_text}
    }
    try:
        response = requests.post(GRAPH_API_URL, params=params, headers=headers, json=data)
        if response.status_code != 200:
            app.logger.error(f"Gửi tin nhắn thất bại: {response.text}")
    except Exception as e:
        app.logger.error(f"Lỗi khi gọi Graph API: {e}")

def perform_unlock(ff_id, recipient_id):
    driver = None
    try:
        options = Options()
        options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=options)
        driver.get('https://unlockffbeta.com/')
        
        wait = WebDriverWait(driver, 35)
        
        # Đợi ô nhập liệu sẵn sàng
        id_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input")))
        driver.execute_script("arguments[0].scrollIntoView();", id_input)
        
        # Dùng Javascript để nhập UID (Sửa lỗi invalid element state)
        driver.execute_script("arguments[0].value = arguments[1];", id_input, ff_id)
        
        # Tìm và Click nút Unlock bằng JS
        unlock_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Unlock')]")))
        driver.execute_script("arguments[0].click();", unlock_btn)
        
        # Kiểm tra kết quả 100%
        try:
            wait.until(EC.text_to_be_present_in_element((By.XPATH, "//body"), "100%"), timeout=60)
            result = f"✅ Unlock thành công ID {ff_id}!\n\nĐã mở khóa tạm thời 2 giờ.\nHết hạn gửi lại lệnh /unlock {ff_id} để tiếp tục nhé! 🚀"
        except TimeoutException:
            # Kiểm tra xem có thông báo lỗi trên web không
            body_text = driver.find_element(By.TAG_NAME, "body").text
            if "not found" in body_text.lower():
                result = f"❌ ID {ff_id} không tồn tại hoặc sai UID. Vui lòng kiểm tra lại!"
            else:
                result = f"❌ Unlock thất bại ID {ff_id}!\n\nWeb đang quá tải hoặc ID không bị khóa Beta. Thử lại sau!"
        
        send_message(recipient_id, result)
        
    except Exception as e:
        app.logger.error(f"Lỗi Selenium chi tiết: {str(e)}")
        send_message(recipient_id, "❌ Hệ thống bận hoặc Web gốc đang lỗi. Thử lại sau 1 phút!")
    finally:
        if driver:
            driver.quit()

@app.route('/', methods=['GET'])
def verify():
    # Xác thực Webhook với Meta (Sửa lỗi 500)
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        app.logger.info("Xác thực Webhook thành công!")
        return challenge, 200
    
    return "Bot FF đang chạy ổn định. Vui lòng sử dụng Webhook của Meta để kết nối.", 200

@app.route('/', methods=['POST'])
def webhook():
    data = request.get_json()
    if data.get('object') == 'page':
        for entry in data['entry']:
            for messaging in entry.get('messaging', []):
                sender_id = messaging['sender']['id']
                if 'message' in messaging and 'text' in messaging['message']:
                    text = messaging['message']['text'].strip()
                    
                    # Nhận dạng lệnh /unlock [ID]
                    match = re.match(r'^/unlock\s+(\d{8,11})$', text, re.IGNORECASE)
                    if match:
                        ff_id = match.group(1)
                        send_message(sender_id, f"🔄 Đang xử lý ID {ff_id}... Chờ khoảng 1 phút nhé!")
                        threading.Thread(target=perform_unlock, args=(ff_id, sender_id)).start()
                    else:
                        send_message(sender_id, "Sai cú pháp! Gửi: /unlock [UID]\nVí dụ: /unlock 12345678")
    return "OK", 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)


