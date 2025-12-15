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
# ==========================================
# HÀM PHỤ: LẤY DỮ LIỆU TỪ DB ĐỂ DẠY AI
# ==========================================
def get_schedule_context(sv_id):
    """Lấy danh sách deadline từ DB và chuyển thành văn bản để AI đọc hiểu"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT TieuDe, MonHocID, ThoiGianKetThuc, MucDoQuanTrong, DiemUuTien 
            FROM LichTrinh 
            WHERE SinhVienID = ? 
            ORDER BY DiemUuTien DESC
        """
        cursor.execute(query, sv_id)
        rows = cursor.fetchall()
        
        if not rows:
            return "Hiện tại sinh viên chưa có lịch trình nào trong danh sách."
            
        # Biến dữ liệu SQL thành đoạn văn bản mô tả
        context_text = "Danh sách lịch trình/deadline hiện tại của sinh viên:\n"
        for row in rows:
            # Format ngày giờ cho dễ đọc
            time_str = row[2].strftime("%d/%m/%Y %H:%M") if row[2] else "Không rõ"
            context_text += f"- Môn {row[1]}: {row[0]} (Hạn: {time_str}, Quan trọng: {row[3]}/5, Điểm ưu tiên: {row[4]:.1f})\n"
            
        return context_text
    except Exception as e:
        return f"Lỗi khi đọc dữ liệu: {str(e)}"
    finally:
        if conn: conn.close()

# ==========================================
# API CHAT (ĐÃ NÂNG CẤP ĐỂ ĐỌC DATABASE)
# ==========================================
@app.route('/api/chat', methods=['POST'])
def chat():
    if not model_gemini: 
        return jsonify({"reply": f"Lỗi AI: Không tìm thấy model ({active_model_name})"}), 500
    
    data = request.json or {}
    user_msg = data.get('message', '')
    sv_id = 'SV001' # Mặc định lấy của SV001
    
    try:
        # 1. Lấy dữ liệu deadline mới nhất từ DB
        db_context = get_schedule_context(sv_id)
        
        # 2. Tạo "Prompt hệ thống" để AI biết nó là ai và đang nắm dữ liệu gì
        system_instruction = (
            f"Bạn là một trợ lý học tập thông minh.\n"
            f"Dưới đây là dữ liệu thực tế từ cơ sở dữ liệu của sinh viên:\n"
            f"---------------------\n"
            f"{db_context}\n"
            f"---------------------\n"
            f"Hãy trả lời câu hỏi của sinh viên dựa trên dữ liệu trên. "
            f"Nếu sinh viên hỏi về việc phải làm, hãy nhắc nhở dựa trên 'Điểm ưu tiên' và 'Hạn nộp'. "
            f"Nếu không liên quan đến lịch trình, hãy trả lời kiến thức bình thường.\n"
            f"Câu hỏi của sinh viên: {user_msg}"
        )

        # 3. Xử lý lịch sử chat (History)
        history = []
        for m in data.get('history', []):
            role = "user" if m.get('role') == "user" else "model"
            content = m.get('content', '')
            if content:
                history.append({"role": role, "parts": [content]})
        
        # 4. Gửi tin nhắn đã ghép context cho AI
        chat_session = model_gemini.start_chat(history=history)
        
        # Lưu ý: Chúng ta gửi system_instruction thay vì chỉ gửi user_msg đơn thuần
        response = chat_session.send_message(system_instruction)
        
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