def optimize_schedule(tasks):
    """
    Sắp xếp danh sách nhiệm vụ dựa trên Điểm Ưu Tiên (DiemUuTien).
    tasks: Danh sách các dictionary.
    """
    # Sắp xếp giảm dần (reverse=True): Điểm cao làm trước
    sorted_tasks = sorted(tasks, key=lambda x: x.get('DiemUuTien') or 0, reverse=True)
    return sorted_tasks