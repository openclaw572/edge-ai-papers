// Edge AI 論文報告網站 - 主應用程式

// 從 reports/index.json 載入報告索引
async function loadReportIndex() {
    try {
        const response = await fetch('reports/index.json');
        if (!response.ok) throw new Error('Failed to load index');
        return await response.json();
    } catch (error) {
        console.error('Error loading report index:', error);
        return { dates: [] };
    }
}

// 渲染側欄日期導航
function renderDateNav(index) {
    const nav = document.getElementById('date-nav');
    nav.innerHTML = '';

    if (!index.dates || index.dates.length === 0) {
        nav.innerHTML = '<p style="color: #95a5a6;">暫無報告</p>';
        return;
    }

    // 按日期排序（新到舊）
    index.dates.sort((a, b) => new Date(b.date) - new Date(a.date));

    index.dates.forEach(dateEntry => {
        const dateGroup = document.createElement('div');
        dateGroup.className = 'date-group';

        const dateTitle = document.createElement('div');
        dateTitle.className = 'date-item';
        dateTitle.textContent = `📅 ${dateEntry.date}`;
        dateTitle.dataset.date = dateEntry.date;
        dateTitle.onclick = () => loadDateReports(dateEntry.date);

        const paperLinks = document.createElement('div');
        paperLinks.className = 'paper-links';
        paperLinks.id = `papers-${dateEntry.date}`;
        paperLinks.style.display = 'none'; // 初始隱藏

        dateEntry.papers.forEach((paper, idx) => {
            const link = document.createElement('a');
            link.className = 'paper-link';
            link.textContent = paper.title || `論文 ${idx + 1}`;
            link.href = '#';
            link.onclick = (e) => {
                e.preventDefault();
                loadPaper(dateEntry.date, idx);
            };
            paperLinks.appendChild(link);
        });

        dateGroup.appendChild(dateTitle);
        dateGroup.appendChild(paperLinks);
        nav.appendChild(dateGroup);
    });
}

// 載入特定日期的報告列表
async function loadDateReports(date) {
    try {
        const response = await fetch(`reports/${date}/index.json`);
        if (!response.ok) throw new Error('Failed to load date reports');
        const dateReports = await response.json();

        // 更新頁面標題
        document.getElementById('page-title').textContent = `📅 ${date} 的論文報告`;

        // 顯示論文選擇卡片
        renderPaperSelector(dateReports);

        // 展開側欄該日期的論文連結
        document.querySelectorAll('.paper-links').forEach(el => el.style.display = 'none');
        const paperLinks = document.getElementById(`papers-${date}`);
        if (paperLinks) paperLinks.style.display = 'flex';

        // 標記活躍日期
        document.querySelectorAll('.date-item').forEach(el => el.classList.remove('active'));
        document.querySelector(`[data-date="${date}"]`).classList.add('active');

    } catch (error) {
        console.error('Error loading date reports:', error);
        document.getElementById('content-area').innerHTML = 
            '<div class="welcome-message"><p>載入失敗，請稍後再試</p></div>';
    }
}

// 渲染論文選擇器
function renderPaperSelector(dateReports) {
    const contentArea = document.getElementById('content-area');
    contentArea.innerHTML = '';

    const selector = document.createElement('div');
    selector.className = 'paper-selector';

    dateReports.papers.forEach((paper, idx) => {
        const card = document.createElement('div');
        card.className = 'paper-card';
        card.onclick = () => loadPaper(dateReports.date, idx);

        const type = paper.type || (idx === 0 ? 'Edge AI' : 'Edge AI Security');
        const typeEmoji = idx === 0 ? '🤖' : '🔒';

        card.innerHTML = `
            <div class="paper-type">${typeEmoji} ${type}</div>
            <h4>${paper.title || '論文標題'}</h4>
            <div class="paper-abstract">${paper.abstract || '點擊查看完整報告'}</div>
        `;

        selector.appendChild(card);
    });

    contentArea.appendChild(selector);
}

// 載入並顯示單篇論文報告
async function loadPaper(date, paperIndex) {
    try {
        const response = await fetch(`reports/${date}/paper-${paperIndex + 1}.md`);
        if (!response.ok) throw new Error('Failed to load paper');
        
        const markdown = await response.text();
        const html = parseMarkdown(markdown);

        document.getElementById('page-title').textContent = `📄 論文報告`;
        document.getElementById('content-area').innerHTML = html;

        // 更新側欄活躍狀態
        document.querySelectorAll('.paper-link').forEach(el => el.classList.remove('active'));
        const paperLinks = document.getElementById(`papers-${date}`);
        if (paperLinks) {
            paperLinks.querySelectorAll('.paper-link')[paperIndex].classList.add('active');
        }

    } catch (error) {
        console.error('Error loading paper:', error);
        document.getElementById('content-area').innerHTML = 
            '<div class="welcome-message"><p>載入報告失敗，請稍後再試</p></div>';
    }
}

// 簡易 Markdown 解析器
function parseMarkdown(md) {
    let html = md;

    // 標題
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

    // 粗體
    html = html.replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>');

    // 列表
    html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^\d+\. (.*$)/gim, '<li>$1</li>');

    // 段落
    html = html.replace(/\n\n/gim, '</p><p>');

    // 連結
    html = html.replace(/\[(.*)\]\((.*)\)/gim, '<a href="$2">$1</a>');

    // 包裝
    html = `<div class="report-content">${html}</div>`;

    return html;
}

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    const index = await loadReportIndex();
    renderDateNav(index);
});
