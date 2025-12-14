import os
import pyodbc
from dotenv import load_dotenv

load_dotenv()

# Cấu hình Database
# Lưu ý: 'Trusted_Connection=yes' chỉ chạy trên Windows với SQL Server local.
# Nếu chạy Docker hoặc Linux, cần dùng User ID và Password.
DB_SERVER = 'Quiet'      # Tên server SQL của bạn
DB_NAME = 'DatabaseAI'   # Tên database

CONN_STR = (
    f'DRIVER={{ODBC Driver 17 for SQL Server}};'
    f'SERVER={DB_SERVER};'
    f'DATABASE={DB_NAME};'
    f'Trusted_Connection=yes;'
)

def get_db_connection():
    return pyodbc.connect(CONN_STR)

def rank_material_trust(search_results):
    for result in search_results:
        score = 5.0
        url = (result.get("URL") or "").lower()
        title = (result.get("TieuDe") or "").lower()
        
        if '.edu' in url: score += 5.0
        elif '.gov' in url: score += 4.5
        
        if any(k in title for k in ['giáo trình', 'bài giảng', 'lecture', 'tutorial', 'pdf']): score += 3.0
        
        if 'wikipedia' in url: score += 1.5
        
        if 'facebook.com' in url or 'tiktok.com' in url: score -= 2.0

        final_score = round((score / 15.0) * 100, 1)
        # Giới hạn điểm từ 1 đến 99
        final_score = max(1.0, min(final_score, 99.0))
        
        result["DiemTinCay"] = final_score
        
    return sorted(search_results, key=lambda x: x.get("DiemTinCay", 0), reverse=True)

def save_ranked_materials(ranked_list):
    if not ranked_list: return

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for item in ranked_list[:5]:
            check_sql = "SELECT COUNT(*) FROM TaiLieu WHERE URL = ?"
            cursor.execute(check_sql, (item.get('URL', ''),))
            if cursor.fetchone()[0] == 0:
                insert_sql = """
                    INSERT INTO TaiLieu (TieuDe, URL, DiemTinCay)
                    VALUES (?, ?, ?)
                """
                cursor.execute(insert_sql, (
                    item.get('TieuDe', '')[:200], 
                    item.get('URL', ''), 
                    item.get('DiemTinCay', 0)
                ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        # Chỉ in lỗi, không làm crash app chính
        print(f"⚠️ Lỗi lưu Database (Module C): {e}")