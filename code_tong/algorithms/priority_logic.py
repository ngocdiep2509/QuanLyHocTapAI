from datetime import datetime

def calculate_priority_score(thoi_gian_ket_thuc_str, muc_do_quan_trong, diem_kho):
    """
    Tính điểm ưu tiên dựa trên Deadline (Urgency), Độ quan trọng (Importance) và Độ khó (Difficulty).
    """
    try:
        # 1. Tính độ khẩn cấp (Urgency)
        deadline = datetime.strptime(thoi_gian_ket_thuc_str, '%Y-%m-%d %H:%M:%S')
        now = datetime.now()
        hours_remaining = (deadline - now).total_seconds() / 3600
        
        if hours_remaining <= 0: return 1000.0 # Quá hạn -> Ưu tiên tối đa
        
        # Càng ít thời gian, điểm càng cao
        if hours_remaining < 24: urgency = 100 - (hours_remaining * 2)
        elif hours_remaining < 72: urgency = 50 - (hours_remaining / 3)
        else: urgency = 10
        
        # 2. Chuẩn hóa các điểm thành phần (Thang 100)
        importance = float(muc_do_quan_trong) * 20 # Input 1-5 -> 20-100
        difficulty = float(diem_kho) * 20           # Input 1-5 -> 20-100

        # 3. Tính tổng có trọng số
        # Khẩn cấp 50% + Quan trọng 30% + Khó 20%
        final_score = (max(0, urgency) * 0.5) + (importance * 0.3) + (difficulty * 0.2)
        
        return round(final_score, 2)
    except Exception as e:
        print(f"Lỗi tính toán Priority: {e}")
        return 0.0