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
# Nên thiết lập trong Environment Variables trên Render
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN', 'EAARFcXJLW0sBQcRahDcP8zME2VsTOMDTnOb8nTMYEp8VIGn8yBR2YIwfRhlL4ih0UOPAPNnB7VRcyZAHGrni9IyTq6ey4cYeQJJHJFMhI6iztc25UDTZA95liSd92FmKfwYrtd18RkayAUtNykbBiZAB7fbiKOgBZCwxYvVA000IzqQOnbceVp6eUKafZCuqTPO1zYwZDZD')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'my_secret_token_123')
GRAPH_API_URL = 'https://graph.facebook.com/v20.0/me/messages'

def send_message(recipient_id, message_text):
    if not PAGE_ACCESS_TOKEN or PAGE_ACCESS_TOKEN == 'DÁN_TOKEN_CỦA_BẠN_VÀO_ĐÂY':
        app.logger.error("LỖI: Chưa có PAGE_ACCESS_TOKEN!")
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
        
        driver = webdriver.Chrome(options=options)
        driver.get('https://unlockffbeta.com/')
        
        # Tăng thời gian chờ lên 45s
        wait = WebDriverWait(driver, 45)
        
        # --- SỬA LỖI Ở ĐÂY ---
        # Thay vì chỉ tìm "presence", ta đợi đến khi ô input thực sự bấm vào được
        id_input = wait.until(EC.element_to_be_clickable((By.XPATH, "//input")))
        
        # Dùng Javascript để xóa và nhập (Mạnh hơn cách nhập thường, tránh lỗi invalid state)
        driver.execute_script("arguments[0].value = '';", id_input)
        id_input.send_keys(ff_id)
        # ---------------------
        
        # Click nút Unlock
        unlock_btn = wait.until(EC.element_to_be_clickable((By.XPATH, 
            "//button[contains(text(), 'Unlock without Discord') or contains(text(), 'Unlock for 2 Hours')]")))
        driver.execute_script("arguments[0].click();", unlock_btn) # Dùng JS click cho chắc ăn
        
        # Đợi kết quả 100%
        try:
            wait.until(EC.text_to_be_present_in_element((By.XPATH, "//body"), "100%"), timeout=60)
            result = f"✅ Unlock thành công ID {ff_id}!\n\nĐã mở khóa tạm thời 2 giờ.\nHết hạn hãy gửi lại lệnh nhé bro! 🚀"
        except TimeoutException:
            result = f"❌ Unlock thất bại ID {ff_id}!\n\nID không tồn tại hoặc web lỗi. Thử lại sau!"
        
        send_message(recipient_id, result)
        
    except Exception as e:
        app.logger.error(f"Lỗi Selenium: {str(e)}")
        send_message(recipient_id, "❌ Lỗi hệ thống: Web đang quá tải hoặc ID bị kẹt. Thử lại sau 1 phút!")
    finally:
        if driver:
            driver.quit()
@app.route('/', methods=['GET'])
def verify():
    # Lấy tham số xác thực từ Meta
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    # Bước quan trọng: Trả về challenge nếu token khớp
    if mode == 'subscribe' and token == VERIFY_TOKEN:
        app.logger.info("Xác thực Webhook THÀNH CÔNG!")
        return challenge, 200
    
    # Trả về trang thông báo thay vì None để tránh lỗi 500
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
                    
                    match = re.match(r'^/unlock\s+(\d{8,11})$', text, re.IGNORECASE)
                    if match:
                        ff_id = match.group(1)
                        send_message(sender_id, f"🔄 Đang xử lý ID {ff_id}... Chờ 30-60 giây nhé!")
                        threading.Thread(target=perform_unlock, args=(ff_id, sender_id)).start()
                    else:
                        send_message(sender_id, "🤦‍♀️Cú pháp: /unlock [UID]😂😒\n🎉Ví dụ: /unlock 134")
    return "OK", 200

if __name__ == '__main__':
    # Render cấp cổng PORT qua biến môi trường
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)



