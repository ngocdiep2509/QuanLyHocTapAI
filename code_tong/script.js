// script.js - Hoàn chỉnh cho Sprint 1
document.addEventListener('DOMContentLoaded', () => {
    const API_BASE = 'http://localhost:5000'; // Chạy cùng origin với Flask

    // Các phần tử giao diện
    const qInput = document.getElementById('q');
    const btnSearch = document.getElementById('btn-search');
    const resDiv = document.getElementById('res');
    const loader = document.getElementById('loader');

    const optimizeForm = document.getElementById('optimizeForm');
    const scheduleBody = document.getElementById('schedule-body');
    const scheduleTable = document.getElementById('schedule-table');
    const messageBox = document.getElementById('message-box');

    const chatBody = document.getElementById('chat-body');
    const chatInput = document.getElementById('chat-input');
    const chatSend = document.getElementById('chat-send');
    const chatToggle = document.getElementById('chat-toggle');
    const chatInputRow = document.getElementById('chat-input-row');

    let conversationHistory = [];

    // Hàm tiện ích
    const show = el => el.classList.remove('hidden');
    const hide = el => el.classList.add('hidden');

    // Hàm xử lý chuỗi tránh lỗi XSS và giữ định dạng xuống dòng
    const esc = s => String(s || '').replace(/[&<>"']/g, c => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": "&#39;"
    }[c]));

    // --- TÍNH NĂNG TÌM KIẾM ---
    async function doSearch() {
        const q = qInput.value.trim();
        if (!q) return;
        resDiv.innerHTML = '';
        show(loader);
        try {
            const resp = await fetch(`${API_BASE}/api/search/material`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query: q })
            });
            const data = await resp.json();
            if (data.status === 'success' && Array.isArray(data.results)) {
                resDiv.innerHTML = data.results.map(item => `
                    <div class="result-card">
                        <div>
                            <h4 class="result-title">${esc(item.TieuDe)}</h4>
                            <a class="result-url" href="${esc(item.URL)}" target="_blank">${esc(item.URL)}</a>
                        </div>
                        <div class="badge">${item.DiemTinCay ?? 50}%</div>
                    </div>`).join('');
            } else {
                resDiv.innerHTML = `<div class="result-card">${esc(data.message || 'Không có kết quả')}</div>`;
            }
        } catch (e) {
            resDiv.innerHTML = `<div class="result-card">Lỗi kết nối tới server tìm kiếm.</div>`;
        } finally {
            hide(loader);
        }
    }
    btnSearch.addEventListener('click', doSearch);
    qInput.addEventListener('keydown', e => { if (e.key === 'Enter') doSearch(); });

    // --- TÍNH NĂNG TỐI ƯU LỊCH ---
    optimizeForm.addEventListener('submit', async e => {
        e.preventDefault();
        scheduleBody.innerHTML = '';
        scheduleTable.classList.add('hidden');
        const sinhVienID = document.getElementById('sinhVienID').value.trim() || 'SV001';
        try {
            const resp = await fetch(`${API_BASE}/api/schedule/optimize`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ SinhVienID: sinhVienID })
            });
            const data = await resp.json();
            if (resp.ok && Array.isArray(data.OptimizedSchedule)) {
                data.OptimizedSchedule.forEach((t, index) => {
                    const tr = document.createElement('tr');
                    tr.innerHTML = `
                        <td><strong>${index + 1}</strong></td>
                        <td>${esc(t.TieuDe)}</td>
                        <td>${esc(t.MonHocID)}</td>
                        <td>${(t.DiemUuTien ?? 0).toFixed(1)}</td>
                        <td>${esc(t.ThoiGianKetThuc)}</td>`;
                    scheduleBody.appendChild(tr);
                });
                scheduleTable.classList.remove('hidden');
            }
        } catch (err) {
            alert('Lỗi kết nối server tối ưu lịch.');
        }
    });

    // --- TÍNH NĂNG CHAT (AI ASSISTANT) ---
    chatToggle.addEventListener('click', () => {
        const isHidden = chatBody.style.display === 'none';
        chatBody.style.display = isHidden ? 'block' : 'none';
        chatInputRow.style.display = isHidden ? 'flex' : 'none';
        chatToggle.textContent = isHidden ? '−' : '+';
    });

    function appendChat(role, text) {
        const el = document.createElement('div');
        el.className = 'chat-message ' + (role === 'user' ? 'user' : 'bot');
        // Chuyển đổi dấu xuống dòng \n thành thẻ <br> để hiển thị đẹp
        el.innerHTML = esc(text).replace(/\n/g, '<br>');
        chatBody.appendChild(el);
        chatBody.scrollTop = chatBody.scrollHeight;
    }

    function appendTyping() {
        const el = document.createElement('div');
        el.className = 'chat-message bot typing';
        el.textContent = 'Đang suy nghĩ...';
        chatBody.appendChild(el);
        chatBody.scrollTop = chatBody.scrollHeight;
        return el;
    }

    async function sendChat() {
        const text = chatInput.value.trim();
        if (!text || chatSend.disabled) return;

        // Hiển thị tin nhắn người dùng
        appendChat('user', text);
        chatInput.value = '';

        // Cập nhật lịch sử (tối đa 20 câu gần nhất để tiết kiệm token)
        conversationHistory.push({ role: 'user', content: text });
        if (conversationHistory.length > 20) conversationHistory.shift();

        // Trạng thái chờ
        chatSend.disabled = true;
        const typingEl = appendTyping();

        try {
            const resp = await fetch(`${API_BASE}/api/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: text,
                    history: conversationHistory
                })
            });

            const data = await resp.json();
            typingEl.remove();

            if (resp.ok) {
                const reply = data.reply || 'AI không có phản hồi.';
                appendChat('assistant', reply);
                conversationHistory.push({ role: 'assistant', content: reply });
            } else {
                appendChat('assistant', 'Lỗi: ' + (data.reply || 'Không thể kết nối AI.'));
            }
        } catch (e) {
            typingEl.remove();
            appendChat('assistant', 'Lỗi kết nối tới server chat.');
        } finally {
            chatSend.disabled = false;
            chatInput.focus();
        }
    }

    chatSend.addEventListener('click', sendChat);
    chatInput.addEventListener('keydown', e => { if (e.key === 'Enter') sendChat(); });

    // Focus vào ô tìm kiếm khi tải trang
    if (qInput) qInput.focus();
});