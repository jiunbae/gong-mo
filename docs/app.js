// IPO 데이터 로드 및 표시
(function() {
    let allData = [];
    let currentFilter = 'upcoming';

    async function loadData() {
        try {
            const response = await fetch('data.json');
            const data = await response.json();

            // 마지막 업데이트 시간 표시
            const lastUpdated = document.getElementById('last-updated');
            if (data.last_updated) {
                const date = new Date(data.last_updated);
                lastUpdated.textContent = formatDate(date);
            }

            allData = data.items || [];
            createMonthFilters();
            renderList();

        } catch (error) {
            console.error('데이터 로드 실패:', error);
            document.getElementById('ipo-list').innerHTML =
                '<p class="loading">데이터를 불러올 수 없습니다.</p>';
        }
    }

    function createMonthFilters() {
        const controls = document.getElementById('filter-controls');
        
        // 현재 날짜 기준 범위 계산
        const today = new Date();
        const targetMonths = [];
        
        // 지난 1개월 (-1) ~ 현재 (0) ~ 앞으로 2개월 (+1, +2)
        for (let i = -1; i <= 2; i++) {
            const d = new Date(today.getFullYear(), today.getMonth() + i, 1);
            const year = d.getFullYear();
            const month = d.getMonth() + 1;
            const monthStr = `${year}-${String(month).padStart(2, '0')}`;
            targetMonths.push({
                key: monthStr,
                label: `${year}년 ${month}월`
            });
        }

        // 월별 버튼 추가
        targetMonths.forEach(mInfo => {
            const btn = document.createElement('button');
            btn.className = 'filter-btn';
            btn.dataset.filter = mInfo.key;
            btn.textContent = mInfo.label;
            btn.addEventListener('click', () => {
                updateFilter(btn, mInfo.key);
            });
            controls.appendChild(btn);
        });

        // 기존 예정/전체 버튼에 이벤트 리스너 재등록
        document.querySelectorAll('.filter-btn').forEach(btn => {
            if (btn.dataset.filter === 'upcoming' || btn.dataset.filter === 'all') {
                btn.addEventListener('click', () => {
                    updateFilter(btn, btn.dataset.filter);
                });
            }
        });
    }

    function updateFilter(clickedBtn, filter) {
        document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
        clickedBtn.classList.add('active');
        currentFilter = filter;
        renderList();
    }

    function formatDate(date) {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        return `${year}-${month}-${day} ${hours}:${minutes}`;
    }

    function formatDateRange(start, end) {
        if (!start) return '-';

        const startDate = new Date(start);
        const startStr = `${startDate.getMonth() + 1}/${startDate.getDate()}`;

        if (end && start !== end) {
            const endDate = new Date(end);
            const endStr = `${endDate.getMonth() + 1}/${endDate.getDate()}`;
            return `${startStr} ~ ${endStr}`;
        }
        return startStr;
    }

    function isPast(dateStr) {
        if (!dateStr) return false;
        const date = new Date(dateStr);
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        return date < today;
    }

    function renderList() {
        const container = document.getElementById('ipo-list');

        let items = allData;
        if (currentFilter === 'upcoming') {
            items = allData.filter(item => !isPast(item.subscription_end || item.subscription_start));
        } else if (currentFilter !== 'all') {
            items = allData.filter(item => {
                if (!item.subscription_start) return false;
                return item.subscription_start.startsWith(currentFilter);
            });
        }

        if (items.length === 0) {
            container.innerHTML = '<p class="loading">표시할 일정이 없습니다.</p>';
            return;
        }

        items.sort((a, b) => {
            const dateA = new Date(a.subscription_start || '9999-12-31');
            const dateB = new Date(b.subscription_start || '9999-12-31');
            return dateA - dateB;
        });

        container.innerHTML = items.map(item => {
            const past = isPast(item.subscription_end || item.subscription_start);
            return `
                <div class="ipo-item${past ? ' past' : ''}">
                    <span class="ipo-badge subscription">청약</span>
                    <div class="ipo-info">
                        <div class="ipo-name">${escapeHtml(item.company_name)}</div>
                        <div class="ipo-details">
                            ${item.offer_price_range || '-'}
                            ${item.lead_underwriter ? '| ' + escapeHtml(item.lead_underwriter) : ''}
                        </div>
                    </div>
                    <div class="ipo-date">
                        ${formatDateRange(item.subscription_start, item.subscription_end)}
                    </div>
                </div>
            `;
        }).join('');
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    loadData();
})();
