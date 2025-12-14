from flask import Flask, request, jsonify
from datetime import datetime
import uuid 
from flask_cors import CORS
import pyodbc 
# Import các hàm từ các file đã tạo:
from database.db_connector import get_db_connection 
from algorithms.priority_logic import calculate_priority_score 
from algorithms.scheduling_logic import optimize_schedule

app = Flask(__name__)
CORS(app)

# [Hàm hỗ trợ: TẠO ID DUY NHẤT]
def generate_custom_id(prefix='LT', length=5):
    """Tạo ID duy nhất, rút gọn, phù hợp với CHAR(5) cho LichTrinhID."""
    # Sử dụng 3 ký tự cuối của UUID để đảm bảo tính ngẫu nhiên, tổng cộng 5 ký tự
    unique_part = uuid.uuid4().hex[-3:].upper()
    return f"{prefix}{unique_part}"


# ==========================================================
# ROUTE 1 (FL-02): TÍNH ĐIỂM ƯU TIÊN VÀ LƯU (CÓ AUTO-CREATE ID)
# ==========================================================

@app.route('/api/deadline/create', methods=['POST'])
def create_deadline():
    data = request.json
    
    # 1. Nhận và chuẩn bị dữ liệu
    mon_hoc_id = data.get('MonHocID')
    muc_do_quan_trong = data.get('MucDoQuanTrong')
    thoi_gian_ket_thuc_str = data.get('ThoiGianKetThuc') 
    sinh_vien_id = data.get('SinhVienID')
    tieu_de = data.get('TieuDe')
    
    if not all([mon_hoc_id, muc_do_quan_trong, thoi_gian_ket_thuc_str, sinh_vien_id, tieu_de]):
        return jsonify({"error": "Thiếu dữ liệu bắt buộc."}), 400

    conn = None
    try:
        # Chuẩn bị thời gian
        # Đảm bảo format thời gian chính xác từ request
        thoi_gian_ket_thuc = datetime.strptime(thoi_gian_ket_thuc_str, '%Y-%m-%d %H:%M:%S')
        thoi_gian_bat_dau = datetime.now() 

        conn = get_db_connection()
        cursor = conn.cursor()

        # ==========================================================
        # 1. AUTO-CREATE SinhVienID (Sử dụng cột HoTen đã sửa)
        # ==========================================================
        cursor.execute("SELECT SinhVienID FROM SinhVien WHERE SinhVienID = ?", sinh_vien_id)
        if cursor.fetchone() is None:
            default_student_name = f"SV Tự Tạo {sinh_vien_id}"
            cursor.execute("INSERT INTO SinhVien (SinhVienID, HoTen) VALUES (?, ?)", 
                           sinh_vien_id, default_student_name) 
            conn.commit()
            print(f"DEBUG: Đã tự động thêm SinhVienID mới: {sinh_vien_id}")
        
        # ==========================================================
        # 2. AUTO-CREATE MonHocID VÀ LẤY DiemKho (Đồng bộ với CSDL mới)
        # ==========================================================
        cursor.execute("SELECT MonHocID, DiemKho FROM MonHoc WHERE MonHocID = ?", mon_hoc_id)
        mon_hoc_result = cursor.fetchone()

        if mon_hoc_result is None:
            # Nếu MonHocID chưa tồn tại, chèn mới.
            default_diem_kho = 3.0 
            default_mon_hoc_name = f"Môn Tự Tạo {mon_hoc_id}"
            
            # ĐÃ SỬA: CHỈ INSERT MonHocID, TenMonHoc, DiemKho (BỎ SinhVienID)
            cursor.execute("INSERT INTO MonHoc (MonHocID, TenMonHoc, DiemKho) VALUES (?, ?, ?)", 
                           mon_hoc_id, default_mon_hoc_name, default_diem_kho)
            conn.commit() 
            
            diem_kho = default_diem_kho 
            print(f"DEBUG: Đã tự động thêm MonHocID mới: {mon_hoc_id} (DiemKho: {diem_kho})")
        else:
            # Nếu MonHocID đã tồn tại, lấy DiemKho từ kết quả truy vấn
            diem_kho = float(mon_hoc_result[1]) 
            print(f"DEBUG: Lấy DiemKho thành công cho {mon_hoc_id}: {diem_kho}")

        
        # ==========================================================
        # 3. CHẠY THUẬT TOÁN TÍNH ĐIỂM ƯU TIÊN (Priority Logic FL-02)
        # ==========================================================
        
        diem_uu_tien = calculate_priority_score(
            thoi_gian_ket_thuc_str, 
            muc_do_quan_trong, 
            diem_kho
        )
        
        # ==========================================================
        # 4. Lưu vào bảng LichTrinh
        # ==========================================================
        
        new_lich_trinh_id = generate_custom_id('LT', 5) 
        
        cursor.execute("""
            INSERT INTO LichTrinh 
            (LichTrinhID, SinhVienID, MonHocID, TieuDe, LoaiSuKien, ThoiGianBatDau, ThoiGianKetThuc, MucDoQuanTrong, DiemUuTien)
            VALUES (?, ?, ?, ?, 'DEADLINE', ?, ?, ?, ?)
        """, 
        new_lich_trinh_id,
        sinh_vien_id, 
        mon_hoc_id, 
        tieu_de, 
        thoi_gian_bat_dau, 
        thoi_gian_ket_thuc, 
        muc_do_quan_trong, 
        diem_uu_tien)
        
        conn.commit()
        
        return jsonify({
            "status": "success",
            "message": "Deadline đã được tạo và điểm ưu tiên đã được tính.",
            "DiemUuTien": f"{diem_uu_tien:.2f}",
            "LichTrinhID_created": new_lich_trinh_id
        }), 200
    
    except ValueError as e:
        # Bắt lỗi format thời gian
        return jsonify({"error": f"Định dạng thời gian không hợp lệ. Cần YYYY-MM-DD HH:MM:SS: {str(e)}"}), 400

    except pyodbc.Error as e:
        # Bắt lỗi pyodbc chung
        if conn: conn.rollback()
        return jsonify({"error": f"Lỗi CSDL: {str(e)}"}), 500

    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": f"Lỗi Server: {str(e)}"}), 500
        
    finally:
        if conn:
            conn.close()

# ==========================================================
# ROUTE 2 (FL-03): Tối Ưu Hóa Lịch Trình (GIỮ NGUYÊN)
# ==========================================================

@app.route('/api/schedule/optimize', methods=['POST'])
def optimize_student_schedule():
    data = request.json
    sinh_vien_id = data.get('SinhVienID')

    if not sinh_vien_id:
        return jsonify({"error": "Vui lòng cung cấp SinhVienID."}), 400

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 1. Truy vấn tất cả deadlines của sinh viên đó
        cursor.execute("""
            SELECT 
                LichTrinhID, TieuDe, MonHocID, ThoiGianKetThuc, DiemUuTien
            FROM 
                LichTrinh 
            WHERE 
                SinhVienID = ?
            ORDER BY 
                ThoiGianKetThuc ASC 
        """, sinh_vien_id)
        
        # Lấy tên cột và chuyển kết quả (tuple) thành danh sách dictionary
        column_names = [desc[0] for desc in cursor.description]
        tasks = []
        for row in cursor.fetchall():
            task = dict(zip(column_names, row))
            if 'DiemUuTien' in task:
                task['DiemUuTien'] = float(task['DiemUuTien'])
            tasks.append(task)
        
        if not tasks:
            return jsonify({"message": "Không tìm thấy nhiệm vụ nào cho sinh viên này.", "OptimizedSchedule": []}), 200

        # 2. CHẠY THUẬT TOÁN FL-03 (Sắp xếp theo Điểm Ưu Tiên)
        optimized_schedule = optimize_schedule(tasks)

        return jsonify({
            "status": "success",
            "SinhVienID": sinh_vien_id,
            "OptimizedSchedule": optimized_schedule
        }), 200
        
    except Exception as e:
        if conn: conn.rollback()
        return jsonify({"error": f"Lỗi Server khi tối ưu hóa: {str(e)}"}), 500
        
    finally:
        if conn:
            conn.close()
            
if __name__ == '__main__':
    app.run(debug=True, port=5000)