// --- CẤU HÌNH ---
const API_BASE = 'http://127.0.0.1:5001';
let chatHistory = [];
let isChatOpen = true;

// 1. CHUYỂN TAB
function switchTab(tabId) {
    document.querySelectorAll('.content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
    document.getElementById('tab-' + tabId).classList.add('active');
    
    const buttons = document.querySelectorAll('.tab-btn');
    if (tabId === 'search') buttons[0].classList.add('active');
    else {
        buttons[1].classList.add('active');
        loadSchedule(); // Tự động tải danh sách khi mở tab
    }
}

// 2. TÌM KIẾM
async function doSearch() {
    const query = document.getElementById('q').value.trim();
    const resDiv = document.getElementById('search-res');
    if (!query) { alert("Vui lòng nhập từ khóa!"); return; }
    
    resDiv.innerHTML = '<div style="text-align:center; margin-top:20px;">⏳ Đang tìm kiếm...</div>';
    try {
        const resp = await fetch(`${API_BASE}/api/search/material`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        const data = await resp.json();
        if (data.status === 'success' && data.results.length > 0) {
            resDiv.innerHTML = data.results.map(i => `
                <div class="res-item">
                    <a href="${i.URL}" target="_blank" class="res-title">${i.TieuDe}</a>
                    <div style="font-size:0.85rem; color:#666;">Độ tin cậy: <strong>${i.DiemTinCay}%</strong></div>
                </div>`).join('');
        } else resDiv.innerHTML = '<div style="text-align:center;">Không tìm thấy kết quả.</div>';
    } catch (e) { resDiv.innerHTML = `<div style="color:red; text-align:center;">Lỗi kết nối Server!</div>`; }
}

// 3. TẠO DEADLINE
async function saveDeadline(e) {
    e.preventDefault();
    const timeVal = document.getElementById('time').value;
    if (!timeVal) { alert("Chọn thời gian!"); return; }

    const payload = {
        SinhVienID: document.getElementById('svID').value,
        MonHocID: document.getElementById('mhID').value,
        TieuDe: document.getElementById('title').value,
        MucDoQuanTrong: document.getElementById('imp').value,
        ThoiGianKetThuc: timeVal.replace('T', ' ') + ':00'
    };

    try {
        const resp = await fetch(`${API_BASE}/api/deadline/create`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json();
        if (data.status === 'success') {
            document.getElementById('dl-result').style.display = 'block';
            document.getElementById('res-score').innerText = data.DiemUuTien;
            loadSchedule(); // Tải lại danh sách ngay
        } else alert('Lỗi: ' + data.error);
    } catch (e) { alert('Lỗi kết nối Server.'); }
}

// 4. HIỂN THỊ DANH SÁCH (CÓ NÚT XÓA)
async function loadSchedule() {
    const listDiv = document.getElementById('schedule-list');
    const svID = document.getElementById('svID').value || 'SV001';
    
    listDiv.innerHTML = '<div style="padding:20px; text-align:center;">⏳ Đang tải...</div>';

    try {
        const resp = await fetch(`${API_BASE}/api/schedule/optimize`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ SinhVienID: svID })
        });
        const data = await resp.json();

        if (data.status === 'success') {
            const tasks = data.OptimizedSchedule;
            if (tasks.length === 0) {
                listDiv.innerHTML = '<div style="padding:20px; text-align:center; color:#718096;">Chưa có deadline nào.</div>';
                return;
            }

            listDiv.innerHTML = tasks.map((task, index) => {
                let color = task.DiemUuTien > 80 ? '#e53e3e' : (task.DiemUuTien > 50 ? '#d69e2e' : '#4a5568');
                const timeShow = task.ThoiGianKetThuc.replace('T', ' ').slice(0, 16);

                return `
                <div style="padding:15px; border-bottom:1px solid #edf2f7; display:flex; justify-content:space-between; align-items:center; background:#fff;">
                    <div style="flex: 1;">
                        <div style="font-weight:600; color:#2d3748;">
                            <span style="color:#718096; font-size:0.8rem; margin-right:5px;">#${index+1}</span>
                            ${task.TieuDe} 
                            <span style="font-size:0.8rem; background:#edf2f7; padding:2px 6px; border-radius:4px;">${task.MonHocID}</span>
                        </div>
                        <div style="font-size:0.85rem; color:#718096;">📅 Hạn: ${timeShow}</div>
                    </div>
                    
                    <div style="text-align:right; display:flex; align-items:center; gap: 15px;">
                        <div>
                            <div style="font-size:1.1rem; font-weight:bold; color:${color};">${parseFloat(task.DiemUuTien).toFixed(1)}</div>
                            <div style="font-size:0.7rem; color:#a0aec0;">Điểm</div>
                        </div>
                        <button onclick="deleteDeadline('${task.LichTrinhID}')" style="background:#fee2e2; border:none; border-radius:50%; width:30px; height:30px; cursor:pointer; display:flex; align-items:center; justify-content:center; color:#c53030; font-size:1rem;">
                            🗑️
                        </button>
                    </div>
                </div>`;
            }).join('');
        }
    } catch (e) { listDiv.innerHTML = '<div style="text-align:center; color:red;">Lỗi tải dữ liệu.</div>'; }
}

// 5. HÀM XỬ LÝ XÓA
async function deleteDeadline(id) {
    if (!confirm("Bạn có chắc chắn muốn xóa deadline này không?")) return;

    try {
        const resp = await fetch(`${API_BASE}/api/deadline/delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ LichTrinhID: id })
        });
        const data = await resp.json();
        
        if (data.status === 'success') {
            // Xóa thành công thì load lại danh sách
            loadSchedule();
        } else {
            alert("Lỗi xóa: " + (data.error || "Unknown"));
        }
    } catch (e) {
        alert("Lỗi kết nối Server khi xóa.");
    }
}

// 6. CHAT
function toggleChat() {
    const box = document.getElementById('chatBox');
    const icon = document.getElementById('chat-icon');
    if (isChatOpen) { box.style.display = 'none'; icon.innerText = '▲'; } 
    else { box.style.display = 'flex'; icon.innerText = '▼'; }
    isChatOpen = !isChatOpen;
}

async function sendChat() {
    const input = document.getElementById('chatInp');
    const msg = input.value.trim();
    if (!msg) return;
    const box = document.getElementById('chatBox');
    
    box.innerHTML += `<div class="msg user">${msg}</div>`;
    input.value = '';
    chatHistory.push({role:'user', content:msg});
    box.scrollTop = box.scrollHeight;
    
    const load = document.createElement('div'); load.className='msg bot'; load.innerText='...'; box.appendChild(load);
    try {
        const res = await fetch(`${API_BASE}/api/chat`, { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:msg, history:chatHistory}) });
        const data = await res.json();
        load.remove();
        const reply = (data.reply||'Lỗi AI').replace(/\n/g, '<br>');
        box.innerHTML += `<div class="msg bot">${reply}</div>`;
        chatHistory.push({role:'model', content:data.reply});
    } catch(e) { load.remove(); box.innerHTML+=`<div class="msg bot" style="color:red">Lỗi mạng.</div>`; }
    box.scrollTop = box.scrollHeight;
}