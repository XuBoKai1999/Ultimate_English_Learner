# English Reader — Architecture v0

> Last synchronized with implementation: 2026-08-27 15:13:01 +08:00

## 1. Goal

建立一個使用真實英文文章學習的本地程式。

核心流程：

```text
找到文章
→ AI 清理文章
→ 匯入清理後文章
→ AI 分析
→ AI 產生單字片語卡
→ 程式整理與儲存
→ TTS
→ 閱讀與複習
```

原則：

- 優先完成最小可運作流程。
- 如無必要，不新增模組、抽象層或資料實體。
- AI 與程式之間以固定文字或 JSON 格式交接。
- 保留未來自動化 AI 的可能，但 v0 不實作 AI API。

------

## 2. Main GUI

GUI 有四個主要入口：

| 頁面               | 功能                    |
| ------------------ | ----------------------- |
| **Daily Learning** | 今日複習 + 建議閱讀來源 |
| **New Article**    | 建立新教材              |
| **Old Articles**   | 閱讀與管理既有教材      |
| **Material Generation Tasks** | 查看背景音訊任務與進度 |

### 2.1 Daily Learning

顯示：

- 今日到期的單字片語卡；
- 建議尋找新文章的來源。

來源與分類見 `categories.md`。

v0 僅顯示來源名稱，不提供網站連結、不自動抓取或推薦具體文章。

GUI 直接讀取 `categories.md` 的 Default Categories 表格，逐項顯示 Category、範圍與建議來源，避免文件與介面各自維護不同清單。

### 2.2 New Article

只負責建立教材。

流程：

```text
AI-cleaned article input
→ article.md
→ Stage 1 AI analysis
→ analysis.json
→ Stage 2 card generation
→ cards.json
→ import / split
→ save
→ background TTS
```

完成後教材進入 Library。

閱讀教材由 `Old Articles` 負責。

閱讀頁的功能控制使用較小字型；Article、Vocabulary List 與卡片正文使用較大內容字型。GUI 縮放時兩級字型維持比例同步縮放。

Article 分頁頂端顯示完整音訊時間軸，下方左側為正文、右側為功能區。Vocabulary Cards 分頁左側為短音訊控制與清單，右側為卡片內容；卡片音訊不顯示時間軸。

切換分頁時立即停止音訊；進入 Article 分頁時立即將播放器來源重設為文章音訊，但將 MP3 解碼延後至上方播放器 Play 或文章雙擊操作，避免播放器保留上一張單字卡音訊，也避免分頁切換卡頓。

背景建置狀態由 `Material Generation Tasks` 負責；使用者可離開頁面並繼續建立其他文章。

### 2.3 Old Articles

依下列方式瀏覽：

```text
Category
└── Year
    └── Month
        └── Article
```

文章頁提供：

- 清理後原文；
- 全文 TTS；
- 該文章的單字片語卡；
- 單字、片語與例句 TTS。

------

## 3. Article Unit

每篇文章視為一個學習單元。

概念上：

```text
Article Unit
├── article.md (cleaned article)
├── analysis
├── cards
└── audio
```

單字卡：

- 屬於其來源文章；
- 同時可被 Daily Learning 獨立引用。

不要為每日複習複製卡片內容。

------

## 4. AI Workflow

v0 的所有 AI 操作均由使用者手動完成。

程式不得直接呼叫 AI API。

### Before Import — Article Cleaning

使用：

```text
prompts/clean_article.md
```

使用者先在同一個 AI 對話提供下列內容：

```text
raw article or page HTML
```

AI 輸出清理後文章，使用者再貼入 GUI：

```text
cleaned article text
```

AI 負責辨識並移除導覽、廣告、cookie、newsletter、推薦內容與其他網頁雜訊，保留文章標題、小標與正文。程式只接收清理後文字並保存為 `article.md`，不保存清理前內容，也不自行清理。

### Stage 1 — Article Analysis

使用：

```text
prompts/analyze_article.md
```

接續同一個 AI 對話，依據剛剛清理完成的文章：

```text
cleaned article
```

輸出：

```text
analysis.json
```

AI 負責：

- 選擇一個既有 Category；
- 擷取值得注意的 word / phrase / chunk；
- 將項目分為：
  - `general`
  - `domain`
  - `specialized`

詳細規則與 JSON schema 以 `analyze_article.md` 為準。

### Stage 2 — Card Generation

使用：

```text
prompts/generate_cards.md
```

接續同一個 AI 對話，依據先前清理文章與剛剛產生的 analysis JSON：

```text
cleaned article
+ analysis.json
```

輸出：

```text
cards.json
```

AI 一次產生全部卡片。

每張卡包含教材內容，例如：

```text
text
type
level
meaning_zh
example_en
example_zh
```

詳細 JSON schema 以 `generate_cards.md` 為準。

AI 不產生：

- ID；
- filename；
- path；
- 日期；
- review state；
- TTS metadata；
- 其他可由程式確定的資料。

------

## 5. AI Integration Boundary

三個 prompt 分別保存，但設計成可在同一個 AI 對話依序貼上。GUI 的 Copy 只複製當前 prompt，不附加文章、analysis JSON 或上一階段輸出。

人工交接流程：

```text
程式準備輸入
→ 使用者手動交給 AI
→ AI 產生 JSON
→ 使用者匯回程式
→ 程式驗證並繼續
```

程式只依賴固定輸入與輸出格式，不依賴特定 AI 模型。

未來可將人工步驟替換為：

```text
Automatic AI API
```

但 v0 不為此預先建立 service layer、API client 或其他額外 abstraction。

------

## 6. Categories

使用 `categories.md` 定義的 Categories。

規則：

1. AI 必須選擇一個既有 Category。
2. 無合理分類時使用 `Uncategorized`。
3. v0 GUI 尚未提供修改文章 Category。
4. 新增 Category 需同步修改 `categories.md`、程式設定與 Library 骨架；v0 尚無管理介面。
5. AI 不自行建立 Category。

Category 用於文章管理，不要求嚴格學術分類。

------

## 7. Cards

Stage 2 產生單一批次檔案：

```text
cards.json
```

程式匯入後，再將卡片拆成可獨立管理的單張資料：

```text
cards.json
→ split
→ individual cards
```

拆分、ID、來源關聯與學習狀態均由程式處理。

每張卡至少需要保留：

### Learning content

```text
text
type
level
meaning_zh
example_en
example_zh
article reference
```

### Learning state

```text
status
review_stage
review_count
last_review
next_review
```

不要要求 AI 產生 learning state。

------

## 8. Review

v0 使用固定間隔的 spaced repetition。

複習間隔集中設定，不將數值散落 hard-code 在各處。

卡片至少支援：

```text
learning
known
```

規則：

- `learning`：進入正常複習排程。
- `known`：不再進入正常 Daily Learning 推送。

Daily Learning 取得：

```text
next_review <= today
AND status == learning
```

的既有卡片。

不建立每日卡片副本。

暫不實作 FSRS。

------

## 9. TTS

TTS 是跨程式共用功能。

教材在建立流程完成時，使用 `edge-tts` 預先產生自然語音 MP3；播放按鈕不得臨時生成音訊。此服務不需要 API key，但生成時需要網路。

生成工作在背景執行，不阻塞 GUI。每篇文章各自顯示一條完成進度與成功／失敗狀態，並允許失敗任務重試。

任務清單只保存在目前程式執行期間；關閉程式會終止 daemon 背景工作，尚未實作跨啟動持久化或續傳。

支援：

- 整篇文章；
- 單字或片語；
- 例句。

同時保存 `WordBoundary` timing JSON，供播放器顯示目前朗讀位置。

播放器至少提供：

- 播放與暫停；
- 停止；
- 從頭重播；
- 拖曳播放進度；
- 在文章框反白目前朗讀字詞所在的顯示行，並自動捲動使其保持可見；
- 雙擊文章文字可將音訊跳至最接近的對應字詞；
- 在單字卡區直接播放該卡的單字／片語及例句音訊。

文字資料是 source of truth。

音訊是 derived data，可重新生成。

------

## 10. Storage

文章依：

```text
Category / Year / Month
```

管理。

文字與音訊使用鏡像目錄。

```text
library/
├── text/
│   └── Category/
│       └── YYYY/
│           └── MM/
│               └── article-id/
│
└── audio/
    └── Category/
        └── YYYY/
            └── MM/
                └── article-id/
```

文字側至少保存：

```text
article.md
analysis.json
cards.json
cards/
```

其中：

- `article.md`：清理後文章；
- `analysis.json`：Stage 1 AI 原始輸出；
- `cards.json`：Stage 2 AI 批次原始輸出；
- `cards/`：程式拆分後的獨立卡片。

音訊側保存對應 TTS 檔案。

```text
article.mp3
article.timing.json
cards/
└── card_XXX/
    ├── text.mp3
    ├── text.timing.json
    ├── example.mp3
    └── example.timing.json
```

不要將音訊視為 canonical data。

------

## 11. Source Suggestions

Daily Learning 可依 `categories.md` 提供建議閱讀來源。

v0：

- 直接解析 `categories.md`，按 Category 顯示範圍與來源名稱；
- 可兼顧使用者興趣與閱讀廣度；
- 不自動下載文章；
- 不自動選擇具體文章。

------

## 12. v0 Boundaries

除非後續明確要求，v0 不實作：

- STT；
- AI API；
- FSRS；
- Anki integration；
- Email / Gmail ingestion；
- automatic web scraping；
- automatic article recommendation；
- complex vocabulary scoring；
- cloud sync；
- multi-user support。

不要為上述功能預先建立架構。

------

## 13. Implementation Rules

- 先完成完整的最小資料流程，再改善介面。
- 驗證 AI 匯入 JSON，再進入後續處理。
- AI 處理正文辨識、清理與其他需要語義判斷的工作。
- 所有 AI 指令以 `prompts/` 內檔案為唯一來源；GUI 在需要人工 AI 操作時顯示對應指令，允許暫時修改與一鍵複製，不在程式碼內重複保存 prompt 內容。
- GUI 中的 prompt 修改不得自動改寫原檔；只有使用者按下保存並再次確認覆蓋後，才更新 `prompts/` 內檔案。
- deterministic 工作交給程式。
- 使用 reference 取代不必要的資料複製。
- 優先使用簡單檔案與小型函式。
- 不為尚未存在的需求建立 abstraction。
- 不自行增加本文件未要求的功能。
- 新增 dependency 前，先確認現有工具無法合理完成。
