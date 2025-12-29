import os
import re
import threading
import requests
from flask import Flask, request
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

app = Flask(__name__)

# Lấy Token từ Variables của Koyeb
PAGE_ACCESS_TOKEN = os.environ.get('PAGE_ACCESS_TOKEN')
VERIFY_TOKEN = os.environ.get('VERIFY_TOKEN', 'my_secret_token_123')

def send_message(recipient_id, message_text):
    if not PAGE_ACCESS_TOKEN: return
    url = f"https://graph.facebook.com/v20.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    requests.post(url, json={'recipient': {'id': recipient_id}, 'message': {'text': message_text}})

def perform_unlock(ff_id, recipient_id):
    driver = None
    try:
        options = Options()
        options.add_argument('--headless=new') # Chạy ngầm định dạng mới nhất
        options.add_argument('--no-sandbox') # Bắt buộc cho môi trường Docker
        options.add_argument('--disable-dev-shm-usage') # Chống tràn bộ nhớ đệm
        options.add_argument('--disable-gpu') # Tắt đồ họa để tiết kiệm RAM
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--blink-settings=imagesEnabled=false') # KHÔNG tải ảnh (Tiết kiệm 200MB RAM)
        options.add_argument('--memory-pressure-off')
        options.add_argument('--window-size=800,600') # Thu nhỏ màn hình ảo

        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30) # Giới hạn thời gian tải trang
        
        driver.get('https://unlockffbeta.com/')
        
        wait = WebDriverWait(driver, 25)
        
        # Sử dụng JavaScript để nhập liệu nhằm giảm tải CPU
        id_input = wait.until(EC.presence_of_element_located((By.XPATH, "//input")))
        driver.execute_script("arguments[0].value = arguments[1];", id_input, ff_id)
        
        unlock_btn = wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Unlock')]")))
        driver.execute_script("arguments[0].click();", unlock_btn)
        
        # Chờ thông báo thành công
        try:
            wait.until(EC.text_to_be_present_in_element((By.XPATH, "//body"), "100%"), timeout=35)
            msg = (
                "╔══════════════╗\n"
                "       🔓 UNLOCK THÀNH CÔNG\n"
                "╚══════════════╝\n\n"
                f"👤 ID: {ff_id}\n"
                "✨ Trạng thái: Bypass Thành Công\n"
                "━━━━━━━━━━━━━━━\n"
                "🚀 Chúc bro chơi game vui vẻ!"
            )
        except TimeoutException:
            msg = f"❌ Lỗi: ID {ff_id} không phản hồi từ web gốc."
        
        send_message(recipient_id, msg)
        
    except Exception as e:
        # Gửi log lỗi cụ thể thay vì thông báo chung chung để dễ debug
        send_message(recipient_id, "⚠️ Koyeb 512MB RAM đã đầy. Vui lòng đợi 30 giây để giải phóng bộ nhớ!")
    finally:
        if driver:
            driver.quit() # Giải phóng RAM ngay lập tức

@app.route('/', methods=['GET'])
def verify():
    if request.args.get('hub.verify_token') == VERIFY_TOKEN:
        return request.args.get('hub.challenge'), 200
    return "Bot Online!", 200

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
                        send_message(sender_id, f"🔄 Đang xử lý ID: {ff_id}...\n⌛ Vui lòng đợi trong giây lát!")
                        threading.Thread(target=perform_unlock, args=(ff_id, sender_id)).start()
                    else:
                        # Hướng dẫn sử dụng khi nhắn sai cú pháp
                        send_message(sender_id, "👋 HDSD: Gửi /unlock [ID] để bắt đầu!")
    return "OK", 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
