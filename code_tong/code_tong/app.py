import os
import logging
import requests
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import google.generativeai as genai
from dotenv import load_dotenv

# --- IMPORT MODULE ---
try:
    from database.db_connector import get_db_connection
    from algorithms.priority_logic import calculate_priority_score
    from algorithms.scheduling_logic import optimize_schedule
except ImportError:
    print("⚠️ Cảnh báo: Thiếu file module logic/database.")

load_dotenv()

# --- CẤU HÌNH ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GOOGLE_CX = os.getenv("GOOGLE_CX")
PORT = 5001

# ======================================================
# CẤU HÌNH GEMINI (TỰ ĐỘNG DÒ TÌM MODEL)
# ======================================================
model_gemini = None
active_model_name = "Chưa kết nối"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    print("--- 📡 Đang kết nối AI... ---")
    try:
        # Lấy danh sách model và chọn cái nào dùng được
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                if 'gemini' in m.name:
                    model_gemini = genai.GenerativeModel(m.name)
                    active_model_name = m.name
                    print(f"--- ✅ ĐÃ KẾT NỐI: {active_model_name} ---")
                    break
        if not model_gemini:
             print("--- ❌ Không tìm thấy model AI nào phù hợp ---")
    except Exception as e:
        print(f"--- ❌ Lỗi AI: {str(e)} ---")

# ======================================================
# FLASK SETUP
# ======================================================
base_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=base_dir, static_url_path='')
CORS(app)
logging.basicConfig(level=logging.INFO)

def generate_custom_id(prefix='LT'):
    return f"{prefix}{uuid.uuid4().hex[-3:].upper()}"

# --- ROUTES ---

@app.route('/')
def index():
    return send_from_directory(base_dir, 'index.html')

# API 1: CHAT AI
@app.route('/api/chat', methods=['POST'])
def chat():
    if not model_gemini: 
        return jsonify({"reply": f"Lỗi AI: Không tìm thấy model ({active_model_name})"}), 500
    
    data = request.json or {}
    try:
        history = []
        for m in data.get('history', []):
            role = "user" if m.get('role') == "user" else "model"
            content = m.get('content', '')
            if content:
                history.append({"role": role, "parts": [content]})
        
        chat_session = model_gemini.start_chat(history=history)
        response = chat_session.send_message(data.get('message', ''))
        return jsonify({"reply": response.text})
    except Exception as e:
        return jsonify({"reply": f"Lỗi AI: {str(e)}"}), 500

# API 2: SEARCH
@app.route('/api/search/material', methods=['POST'])
def search_api():
    q = request.json.get('query', '')
    if not GOOGLE_API_KEY: return jsonify({"status":"error", "message":"Thiếu Key Search"}), 500
    try:
        resp = requests.get("https://www.googleapis.com/customsearch/v1", params={'q':q, 'key':GOOGLE_API_KEY, 'cx':GOOGLE_CX}, timeout=5)
        items = resp.json().get('items', []) or []
        results = []
        for i in items:
            link = i.get('link','')
            score = 85 if '.edu' in link else (90 if '.gov' in link else 50)
            results.append({"TieuDe": i.get('title'), "URL": link, "DiemTinCay": score})
        return jsonify({"status":"success","results":results})
    except Exception as e: return jsonify({"status":"error","message":str(e)}), 500

# API 3: TẠO DEADLINE & TÍNH ĐIỂM
@app.route('/api/deadline/create', methods=['POST'])
def create_deadline():
    data = request.json
    conn = None
    try:
        sv_id = data.get('SinhVienID')
        mh_id = data.get('MonHocID')
        tieu_de = data.get('TieuDe')
        do_quan_trong = int(data.get('MucDoQuanTrong', 3))
        thoi_gian_kt = data.get('ThoiGianKetThuc')

        conn = get_db_connection()
        cursor = conn.cursor()

        # Check SinhVien/MonHoc
        cursor.execute("SELECT SinhVienID FROM SinhVien WHERE SinhVienID = ?", sv_id)
        if not cursor.fetchone():
            cursor.execute("INSERT INTO SinhVien (SinhVienID, HoTen) VALUES (?, ?)", sv_id, f"SV {sv_id}")
        
        cursor.execute("SELECT DiemKho FROM MonHoc WHERE MonHocID = ?", mh_id)
        row = cursor.fetchone()
        diem_kho = 3.0
        if not row:
            cursor.execute("INSERT INTO MonHoc (MonHocID, TenMonHoc, DiemKho) VALUES (?, ?, ?)", mh_id, f"Môn {mh_id}", 3.0)
        else:
            diem_kho = float(row[0])
        conn.commit()

        # Tính điểm
        diem_uu_tien = calculate_priority_score(thoi_gian_kt, do_quan_trong, diem_kho)

        # Lưu DB
        new_id = generate_custom_id()
        cursor.execute("""
            INSERT INTO LichTrinh (LichTrinhID, SinhVienID, MonHocID, TieuDe, LoaiSuKien, ThoiGianBatDau, ThoiGianKetThuc, MucDoQuanTrong, DiemUuTien)
            VALUES (?, ?, ?, ?, 'DEADLINE', GETDATE(), ?, ?, ?)
        """, new_id, sv_id, mh_id, tieu_de, thoi_gian_kt, do_quan_trong, diem_uu_tien)
        conn.commit()

        return jsonify({
            "status": "success",
            "DiemUuTien": f"{diem_uu_tien:.2f}",
            "LichTrinhID_created": new_id
        })
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# API 4: LẤY DANH SÁCH LỊCH TRÌNH (ĐÂY LÀ PHẦN BẠN ĐANG THIẾU)
@app.route('/api/schedule/optimize', methods=['POST'])
def get_optimized_schedule():
    data = request.json
    sv_id = data.get('SinhVienID', 'SV001')
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Lấy dữ liệu từ DB
        query = """
            SELECT LichTrinhID, TieuDe, MonHocID, ThoiGianKetThuc, DiemUuTien, MucDoQuanTrong
            FROM LichTrinh
            WHERE SinhVienID = ?
        """
        cursor.execute(query, sv_id)
        
        columns = [column[0] for column in cursor.description]
        tasks = []
        for row in cursor.fetchall():
            task = dict(zip(columns, row))
            if task['DiemUuTien']: task['DiemUuTien'] = float(task['DiemUuTien'])
            # Convert datetime to string for JSON
            if isinstance(task['ThoiGianKetThuc'], datetime):
                task['ThoiGianKetThuc'] = task['ThoiGianKetThuc'].strftime('%Y-%m-%d %H:%M:%S')
            tasks.append(task)
            
        # Sắp xếp
        final_schedule = optimize_schedule(tasks)
        
        return jsonify({
            "status": "success",
            "SinhVienID": sv_id,
            "OptimizedSchedule": final_schedule
        })

    except Exception as e:
        print(f"Lỗi Optimize: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

# ==========================================
# API 5: XÓA DEADLINE (MỚI THÊM)
# ==========================================
@app.route('/api/deadline/delete', methods=['POST'])
def delete_deadline():
    data = request.json
    id_can_xoa = data.get('LichTrinhID')
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Thực hiện xóa trong DB
        cursor.execute("DELETE FROM LichTrinh WHERE LichTrinhID = ?", id_can_xoa)
        conn.commit()
        
        return jsonify({"status": "success", "message": "Đã xóa thành công!"})
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if conn: conn.close()

if __name__ == '__main__':
    print(f"🚀 Server đang khởi động tại: http://127.0.0.1:{PORT}")
    app.run(host='0.0.0.0', port=PORT, debug=True)