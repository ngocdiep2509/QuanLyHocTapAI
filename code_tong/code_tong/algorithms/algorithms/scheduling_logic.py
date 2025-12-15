def optimize_schedule(tasks):
    """
    Sắp xếp danh sách nhiệm vụ dựa trên Điểm Ưu Tiên (DiemUuTien).
    Input: Danh sách các dictionary nhiệm vụ.
    Output: Danh sách đã sắp xếp giảm dần.
    """
    # Sắp xếp: Key là DiemUuTien, reverse=True (Giảm dần)
    # Nếu task nào không có điểm (None) thì coi như là 0
    sorted_tasks = sorted(tasks, key=lambda x: x.get('DiemUuTien') or 0, reverse=True)
    
    return sorted_tasks