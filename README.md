# Paper Reports Website

這個 repo 只保留靜態網站架構與已發布的論文報告資料。

## 網站架構

```text
index.html          # 靜態網站入口
css/                # 網站樣式
js/                 # 前端邏輯，讀取 reports/index.json 與每日 index
reports/            # 已發布 Markdown 報告與索引
project/paper_report/ # 產生本網站內容的 Paper Report 專案程式與文件
```

## 更新方式

網站前端會讀取：

1. `reports/index.json`：全域日期索引。
2. `reports/YYYY-MM-DD/index.json`：單日 paper 清單。
3. `reports/YYYY-MM-DD/*.md`：單篇繁體中文 Markdown 報告。

新增報告時，只要把 Markdown 放入對應日期資料夾，並更新上述兩個 JSON index，網站就會顯示新內容。
