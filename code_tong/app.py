import os
import logging
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Load biến môi trường
load_dotenv()

# ==========================================
# CẤU HÌNH API KEYS
# ==========================================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")
PORT = 5000

# ==========================================
# CẤU HÌNH GEMINI (SMART AUTO-DETECT)
# ==========================================
model_gemini = None
active_model_name = "None"

def setup_gemini():
    global model_gemini, active_model_name
    
    if not GEMINI_API_KEY:
        print("⚠️ CẢNH BÁO: Chưa có GEMINI_API_KEY trong file .env")
        return

    try:
        genai.configure(api_key=GEMINI_API_KEY)
        print("--- 🔄 Đang tự động dò tìm Model khả dụng cho Key của bạn... ---")
        
        # CÁCH 1: Thử các model tiêu chuẩn trước
        candidates = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']
        for name in candidates:
            try:
                test_model = genai.GenerativeModel(name)
                test_model.generate_content("Hi")
                model_gemini = test_model
                active_model_name = name
                print(f"--- ✅ Kết nối thành công (Ưu tiên): {name} ---")
                return
            except:
                continue

        # CÁCH 2: Nếu thất bại, hỏi Server danh sách model được phép dùng
        print("--- ⚠️ Các model chuẩn thất bại. Đang quét danh sách từ Google... ---")
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        if available_models:
            # Lấy cái đầu tiên tìm thấy
            best_choice = available_models[0]
            model_gemini = genai.GenerativeModel(best_choice)
            active_model_name = best_choice
            print(f"--- ✅ Đã tìm thấy và kích hoạt model: {active_model_name} ---")
        else:
            print("❌ LỖI NGHIÊM TRỌNG: Key của bạn đúng, nhưng không có quyền truy cập model nào.")
            print("👉 Giải pháp: Tạo Key mới tại https://aistudio.google.com/app/apikey")
            
    except Exception as e:
        print(f"❌ LỖI KẾT NỐI GEMINI: {str(e)}")
        print("👉 Kiểm tra lại mạng hoặc Key của bạn.")

# Chạy cấu hình ngay khi khởi động
setup_gemini()

# ==========================================
# THIẾT LẬP FLASK
# ==========================================
base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=base_dir, static_url_path='')
CORS(app)
logging.basicConfig(level=logging.INFO)

# ==========================================
# LOGIC XỬ LÝ (CHẾ ĐỘ AN TOÀN)
# ==========================================
class SafeLogic:
    def rank_material_trust(self, results):
        ranked = []
        for r in results:
            score = 50.0
            url = (r.get("URL") or "").lower()
            if '.edu' in url: score += 30
            elif '.gov' in url: score += 20
            r["DiemTinCay"] = min(99.0, score)
            ranked.append(r)
        return sorted(ranked, key=lambda x: x["DiemTinCay"], reverse=True)
mcl = SafeLogic()

# ==========================================
# ROUTES
# ==========================================
@app.route('/')
def index():
    return send_from_directory(base_dir, 'index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    if not model_gemini:
        # Thử lại lần nữa nếu lúc đầu chưa được
        setup_gemini()
        if not model_gemini:
            return jsonify({"reply": "Lỗi: Server không tìm thấy Model AI nào khả dụng với Key này. Hãy thử tạo Key mới."}), 500

    data = request.json or {}
    user_message = (data.get('message') or '').strip()
    history = data.get('history', []) # Lấy lịch sử chat

    if not user_message:
        return jsonify({"reply": "Bạn chưa nhập tin nhắn."}), 400

    try:
        # Xây dựng lịch sử chat cho Gemini
        gemini_history = []
        for m in history:
            role = "user" if m.get('role') == "user" else "model"
            content = m.get('content', "").strip()
            if content:
                gemini_history.append({"role": role, "parts": [content]})

        # Tạo chat session
        chat = model_gemini.start_chat(history=gemini_history)
        response = chat.send_message(user_message)
        
        return jsonify({
            "reply": response.text.strip(),
            "model": active_model_name
        })
    except Exception as e:
        return jsonify({"reply": f"Lỗi khi chat: {str(e)}"}), 500

@app.route('/api/search/material', methods=['POST'])
def search_api():
    # ... Giữ nguyên logic tìm kiếm ...
    data = request.json or {}
    q = (data.get('query') or '').strip()
    if not GOOGLE_API_KEY: return jsonify({"status":"error", "message":"Thiếu Search Key"}), 500
    try:
        resp = requests.get("https://www.googleapis.com/customsearch/v1", 
                          params={'q': q, 'key': GOOGLE_API_KEY, 'cx': GOOGLE_CX}, timeout=10)
        items = resp.json().get('items', []) or []
        results = [{"TieuDe": i.get('title'), "URL": i.get('link')} for i in items]
        return jsonify({"status":"success","results":mcl.rank_material_trust(results)})
    except Exception as e:
        return jsonify({"status":"error","message":str(e)}), 500

@app.route('/api/schedule/optimize', methods=['POST'])
def optimize_schedule():
    return jsonify({"OptimizedSchedule": [
        {"TieuDe":"Báo cáo AI (Demo)","MonHocID":"AI1","DiemUuTien":90,"ThoiGianKetThuc":"2025-12-20"}
    ]})

if __name__ == '__main__':
    print(f"🚀 Server đang chạy tại http://localhost:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)