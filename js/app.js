// Edge AI 論文報告網站 - 主應用程式

const dateReportCache = new Map();
let reportIndex = { dates: [] };
let selectedCategory = 'review';
let categorizedDates = { review: [], general: [] };

function detectPaperType(paper = {}) {
    const explicit = (paper.paperType || paper.type || '').toLowerCase();
    if (explicit.includes('review') || explicit.includes('survey')) return 'review';
    if (explicit.includes('general')) return 'general';

    const text = `${paper.title || ''} ${paper.category || ''}`.toLowerCase();
    const reviewKeywords = ['review', 'survey', 'systematic review', 'meta-analysis', 'literature review'];
    return reviewKeywords.some((k) => text.includes(k)) ? 'review' : 'general';
}

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

// 讀取特定日期的 index，含快取
async function getDateReports(date) {
    if (dateReportCache.has(date)) return dateReportCache.get(date);
    const response = await fetch(`reports/${date}/index.json`);
    if (!response.ok) throw new Error('Failed to load date reports');
    const data = await response.json();
    dateReportCache.set(date, data);
    return data;
}

async function buildCategories(index) {
    const review = [];
    const general = [];

    const sortedDates = [...(index.dates || [])].sort((a, b) => new Date(b.date) - new Date(a.date));

    for (const dateEntry of sortedDates) {
        try {
            const dateReports = await getDateReports(dateEntry.date);
            const papers = dateReports.papers || [];
            const hasReview = papers.some((p) => detectPaperType(p) === 'review');
            (hasReview ? review : general).push({ ...dateEntry, dateReports });
        } catch (err) {
            console.warn(`Skip date ${dateEntry.date}:`, err.message);
        }
    }

    return { review, general };
}

function bindCategorySwitch() {
    const switcher = document.getElementById('category-switch');
    switcher.querySelectorAll('.category-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            selectedCategory = btn.dataset.category;
            switcher.querySelectorAll('.category-btn').forEach((b) => b.classList.remove('active'));
            btn.classList.add('active');

            renderDateNavByCategory();
            clearContentForCategory();
        });
    });
}

function clearContentForCategory() {
    document.getElementById('page-title').textContent = `已選擇 ${selectedCategory === 'review' ? 'Review Paper' : 'General Paper'}，請選擇日期`;
    document.getElementById('content-area').innerHTML = '<div class="welcome-message"><p>請從側欄選擇日期查看報告。</p></div>';
}

function renderDateNavByCategory() {
    const nav = document.getElementById('date-nav');
    const hint = document.getElementById('category-hint');
    nav.innerHTML = '';

    const list = categorizedDates[selectedCategory] || [];
    hint.textContent = `目前分類：${selectedCategory === 'review' ? 'Review Paper' : 'General Paper'}`;

    if (list.length === 0) {
        nav.innerHTML = '<p style="color: #95a5a6;">此分類暫無報告</p>';
        return;
    }

    list.forEach((dateEntry) => {
        const dateGroup = document.createElement('div');
        dateGroup.className = 'date-group';

        const dateTitle = document.createElement('div');
        dateTitle.className = 'date-item';
        dateTitle.textContent = `📅 ${dateEntry.date}`;
        dateTitle.dataset.date = dateEntry.date;
        dateTitle.onclick = () => loadDateReports(dateEntry.date, dateEntry.dateReports);

        const paperLinks = document.createElement('div');
        paperLinks.className = 'paper-links';
        paperLinks.id = `papers-${dateEntry.date}`;
        paperLinks.style.display = 'none';

        (dateEntry.dateReports?.papers || []).forEach((paper, idx) => {
            const link = document.createElement('a');
            link.className = 'paper-link';
            link.textContent = paper.title || `論文 ${idx + 1}`;
            link.href = '#';
            link.onclick = (e) => {
                e.preventDefault();
                loadPaper(dateEntry.date, paper, idx);
            };
            paperLinks.appendChild(link);
        });

        dateGroup.appendChild(dateTitle);
        dateGroup.appendChild(paperLinks);
        nav.appendChild(dateGroup);
    });
}

// 載入特定日期的報告列表
async function loadDateReports(date, prefetchedReports = null) {
    try {
        const dateReports = prefetchedReports || await getDateReports(date);

        document.getElementById('page-title').textContent = `📅 ${date} 的論文報告`;
        renderPaperSelector(dateReports);

        document.querySelectorAll('.paper-links').forEach((el) => {
            el.style.display = 'none';
        });
        const paperLinks = document.getElementById(`papers-${date}`);
        if (paperLinks) paperLinks.style.display = 'flex';

        document.querySelectorAll('.date-item').forEach((el) => el.classList.remove('active'));
        const active = document.querySelector(`[data-date="${date}"]`);
        if (active) active.classList.add('active');
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

    (dateReports.papers || []).forEach((paper, idx) => {
        const card = document.createElement('div');
        card.className = 'paper-card';
        card.onclick = () => loadPaper(dateReports.date, paper, idx);

        const type = paper.category || paper.type || (idx === 0 ? 'Edge AI' : 'Edge AI Security');
        const typeEmoji = /embedded|嵌入/i.test(type)
            ? '🛡️'
            : idx === 0
                ? '🤖'
                : '🔒';

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
async function loadPaper(date, paper, paperIndex) {
    try {
        const fallbackName = `paper-${paperIndex + 1}.md`;
        const fileName = paper?.file || paper?.path || fallbackName;

        const response = await fetch(`reports/${date}/${fileName}`);
        if (!response.ok) throw new Error('Failed to load paper');

        const markdown = await response.text();
        const html = parseMarkdown(markdown);

        document.getElementById('page-title').textContent = '📄 論文報告';
        document.getElementById('content-area').innerHTML = html;

        document.querySelectorAll('.paper-link').forEach((el) => el.classList.remove('active'));
        const paperLinks = document.getElementById(`papers-${date}`);
        if (paperLinks && paperLinks.querySelectorAll('.paper-link')[paperIndex]) {
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
    const lines = md.split('\n');
    const out = [];
    let inOl = false;
    let inUl = false;

    const closeLists = () => {
        if (inOl) {
            out.push('</ol>');
            inOl = false;
        }
        if (inUl) {
            out.push('</ul>');
            inUl = false;
        }
    };

    const inline = (text) => text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\[(.*?)\]\((.*?)\)/g, '<a href="$2">$1</a>');

    for (const raw of lines) {
        const line = raw.trimEnd();

        if (!line.trim()) {
            closeLists();
            continue;
        }

        const h3 = line.match(/^###\s+(.*)$/);
        if (h3) {
            closeLists();
            out.push(`<h3>${inline(h3[1])}</h3>`);
            continue;
        }

        const h2 = line.match(/^##\s+(.*)$/);
        if (h2) {
            closeLists();
            out.push(`<h2>${inline(h2[1])}</h2>`);
            continue;
        }

        const h1 = line.match(/^#\s+(.*)$/);
        if (h1) {
            closeLists();
            out.push(`<h1>${inline(h1[1])}</h1>`);
            continue;
        }

        const ol = line.match(/^\s*\d+\.\s+(.*)$/);
        if (ol) {
            if (inUl) {
                out.push('</ul>');
                inUl = false;
            }
            if (!inOl) {
                out.push('<ol>');
                inOl = true;
            }
            out.push(`<li>${inline(ol[1])}</li>`);
            continue;
        }

        const ul = line.match(/^\s*[-*]\s+(.*)$/);
        if (ul) {
            if (inOl) {
                out.push('</ol>');
                inOl = false;
            }
            if (!inUl) {
                out.push('<ul>');
                inUl = true;
            }
            out.push(`<li>${inline(ul[1])}</li>`);
            continue;
        }

        closeLists();
        out.push(`<p>${inline(line)}</p>`);
    }

    closeLists();
    return `<div class="report-content">${out.join('')}</div>`;
}

// 初始化
document.addEventListener('DOMContentLoaded', async () => {
    reportIndex = await loadReportIndex();
    bindCategorySwitch();
    categorizedDates = await buildCategories(reportIndex);
    renderDateNavByCategory();
    clearContentForCategory();
});
