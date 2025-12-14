// --- CẤU HÌNH ĐƯỜNG DẪN SERVER ---
const API_BASE = 'http://127.0.0.1:5001';

let chatHistory = [];
let isChatOpen = true;

// 1. CHUYỂN TAB
function switchTab(tabId) {
    document.querySelectorAll('.content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + tabId).classList.add('active');
    
    // Highlight nút bấm
    const buttons = document.querySelectorAll('.tab-btn');
    if (tabId === 'search') {
        buttons[0].classList.add('active');
    } else {
        buttons[1].classList.add('active');
        // Khi chuyển sang tab Deadline thì tự động tải danh sách luôn
        loadSchedule();
    }
}

// 2. TÌM KIẾM
async function doSearch() {
    const query = document.getElementById('q').value.trim();
    const resultDiv = document.getElementById('search-res');
    
    if (!query) { alert("Vui lòng nhập từ khóa!"); return; }
    
    resultDiv.innerHTML = '<div style="text-align:center; margin-top:20px;">⏳ Đang tìm kiếm...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/search/material`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        const data = await response.json();

        if (data.status === 'success' && data.results.length > 0) {
            resultDiv.innerHTML = data.results.map(item => `
                <div class="res-item">
                    <a href="${item.URL}" target="_blank" class="res-title">${item.TieuDe}</a>
                    <div style="font-size:0.85rem; color:#666; margin-top:5px;">
                        Độ tin cậy: <strong>${item.DiemTinCay}%</strong> ${item.DiemTinCay >= 80 ? '✅' : ''}
                    </div>
                </div>
            `).join('');
        } else {
            resultDiv.innerHTML = '<div style="text-align:center;">Không tìm thấy kết quả.</div>';
        }
    } catch (error) { resultDiv.innerHTML = `<div style="color:red; text-align:center;">Lỗi kết nối Server!</div>`; }
}

// 3. TẠO DEADLINE & TÍNH ĐIỂM
async function saveDeadline(event) {
    event.preventDefault();
    const timeVal = document.getElementById('time').value;
    if (!timeVal) { alert("Vui lòng chọn thời gian!"); return; }

    const payload = {
        SinhVienID: document.getElementById('svID').value,
        MonHocID: document.getElementById('mhID').value,
        TieuDe: document.getElementById('title').value,
        MucDoQuanTrong: document.getElementById('imp').value,
        ThoiGianKetThuc: timeVal.replace('T', ' ') + ':00'
    };

    const resultBox = document.getElementById('dl-result');
    resultBox.style.display = 'none';

    try {
        const response = await fetch(`${API_BASE}/api/deadline/create`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        if (data.status === 'success') {
            resultBox.style.display = 'block';
            document.getElementById('res-score').innerText = data.DiemUuTien;
            
            // 🔥 QUAN TRỌNG: Lưu xong thì tải lại danh sách ngay
            loadSchedule();
        } else {
            alert('Lỗi Server: ' + (data.error || data.message));
        }
    } catch (error) { alert('Không thể kết nối Server.'); }
}

// 🔥 4. HÀM MỚI: TẢI DANH SÁCH DEADLINE (LỊCH TRÌNH)
async function loadSchedule() {
    const listDiv = document.getElementById('schedule-list');
    const svID = document.getElementById('svID').value || 'SV001';

    listDiv.innerHTML = '<div style="padding:20px; text-align:center;">⏳ Đang tải dữ liệu...</div>';

    try {
        const response = await fetch(`${API_BASE}/api/schedule/optimize`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ SinhVienID: svID })
        });
        const data = await response.json();

        if (data.status === 'success') {
            const tasks = data.OptimizedSchedule;
            if (tasks.length === 0) {
                listDiv.innerHTML = '<div style="padding:20px; text-align:center; color:#718096;">Chưa có deadline nào.</div>';
                return;
            }

            // Render danh sách (Sắp xếp theo điểm ưu tiên cao nhất)
            listDiv.innerHTML = tasks.map((task, index) => {
                // Đổi màu dựa trên mức độ ưu tiên
                let color = '#4a5568';
                if(task.DiemUuTien > 80) color = '#e53e3e'; // Đỏ (Rất gấp)
                else if(task.DiemUuTien > 50) color = '#d69e2e'; // Vàng
                
                // Format ngày giờ cho đẹp (cắt bỏ phần giây thừa nếu muốn)
                const timeShow = task.ThoiGianKetThuc.replace('T', ' ').slice(0, 16);

                return `
                <div style="padding:15px; border-bottom:1px solid #edf2f7; display:flex; justify-content:space-between; align-items:center; background:#fff;">
                    <div>
                        <div style="font-weight:600; font-size:1rem; color:#2d3748;">
                            <span style="color:#718096; font-size:0.8rem; margin-right:5px;">#${index+1}</span>
                            ${task.TieuDe} 
                            <span style="font-size:0.8rem; background:#edf2f7; padding:2px 6px; border-radius:4px; margin-left:5px;">${task.MonHocID}</span>
                        </div>
                        <div style="font-size:0.85rem; color:#718096; margin-top:4px;">
                            📅 Hạn: ${timeShow}
                        </div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-size:1.2rem; font-weight:bold; color:${color};">
                            ${parseFloat(task.DiemUuTien).toFixed(1)}
                        </div>
                        <div style="font-size:0.7rem; color:#a0aec0;">Điểm Ưu Tiên</div>
                    </div>
                </div>`;
            }).join('');
        }
    } catch (e) {
        listDiv.innerHTML = '<div style="padding:20px; text-align:center; color:red;">Lỗi tải danh sách.</div>';
    }
}

// 5. CHAT WIDGET
function toggleChat() {
    const box = document.getElementById('chatBox');
    const icon = document.getElementById('chat-icon');
    if (isChatOpen) { box.style.display = 'none'; icon.innerText = '▲'; } 
    else { box.style.display = 'flex'; icon.innerText = '▼'; }
    isChatOpen = !isChatOpen;
}

async function sendChat() {
    const input = document.getElementById('chatInp');
    const message = input.value.trim();
    if (!message) return;
    const box = document.getElementById('chatBox');

    box.innerHTML += `<div class="msg user">${message}</div>`;
    input.value = '';
    chatHistory.push({ role: 'user', content: message });
    box.scrollTop = box.scrollHeight;
    
    // Hiệu ứng loading
    const load = document.createElement('div');
    load.className = 'msg bot'; load.innerText = '...';
    box.appendChild(load);

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: message, history: chatHistory })
        });
        const data = await response.json();
        load.remove();
        const reply = (data.reply || 'AI không phản hồi').replace(/\n/g, '<br>');
        box.innerHTML += `<div class="msg bot">${reply}</div>`;
        chatHistory.push({ role: 'model', content: data.reply });
    } catch (error) {
        load.remove();
        box.innerHTML += `<div class="msg bot" style="color:red">Lỗi kết nối.</div>`;
    }
    box.scrollTop = box.scrollHeight;
}