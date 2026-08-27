# English Reader — Architecture v0

> Specification updated: 2026-08-27 17:00:22 +08:00. Step 07 requirements are not yet implemented.

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

- **New Cards**：每日首次學習 cards；
- **History Review**：每日排程複習及 Dictation；
- **Active Dictation**：不限量的主動聽寫；
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

不同文章中的相同 vocabulary 保留為各文章自己的 card，不做跨文章 deduplication、merge、global vocabulary index 或 frequency database。重複出現視為額外 exposure；使用者已熟悉時可將個別 card 標記為 `known`。

------

## 8. Review

v0 直接使用每篇文章既有 card 與 review state，不建立每日副本或另一套狀態。

### 8.1 Central Configuration

下列數值必須集中管理：

```text
MAX_NEW_CARDS_PER_DAY = 15
MAX_HISTORY_CARDS_PER_DAY = 10
INTERVALS = [2, 5, 10, 21, 45, 90, 180]
LEVEL_WEIGHTS = {general: 4, domain: 2, specialized: 1}
OVERDUE_WEIGHTS = {due_today: 1, overdue_1_7: 2, overdue_8_30: 4, overdue_over_30: 8}
AUDIO_CACHE_DAYS = 30
```

不得散落 hard-code，不加入 FSRS。

### 8.2 Status and Stages

至少支援：

```text
learning
graduated
known
```

- `learning`：首次學習或正常排程中；
- `graduated`：完成主要 Dictation intervals，進入 long-term pool；
- `known`：使用者主動表示已會，退出一般排程。

`review_stage` 沿用既有欄位。Stage 0 表示尚未成功完成首次 Dictation；每次成功才加 1。完成最後 interval 後改為 `graduated`。

### 8.3 New Cards

每日最多 15 張。候選為 `status == learning AND review_stage == 0 AND next_review <= today`；成功後進入後續 History Review 排程，失敗則維持 Stage 0 並於明日再派發。

選取時：

- 優先近期文章；
- 依既有 level 權重 `general 4 / domain 2 / specialized 1`；
- 超額留在 backlog；候選不足不補滿；
- 若存在 old backlog，每日至少保留 3 個名額；其餘名額優先最新文章；任一側候選不足時由另一側補位，不為配額留空。

v0 將 old backlog 定義為：article 建立時間早於目前最新 eligible article 的 Stage 0 candidates。保留名額從 old backlog 中優先較舊文章；其餘名額依 article 建立時間由新到舊。相同 article 優先度內使用既有 level weight，最後再隨機。

### 8.4 History Review

每日總上限 10 張，不是每個 stage 各 10 張。主要候選：

```text
next_review <= today
AND status == learning
AND review_stage > 0
```

抽取優先考慮 overdue 程度、level，最後才隨機；基礎權重可使用：

```text
weight = level_weight * overdue_weight
```

overdue 權重為今天到期 ×1、逾期 1–7 天 ×2、8–30 天 ×4、超過 30 天 ×8，避免舊 card 永久沉沒。

History Review 通常為 9 張 learning 加 1 張 `graduated` long-term card。若 graduated pool 為空，該名額改由 learning 補上；若 learning 不足，graduated 可補滿其餘名額。不得只為維持 9:1 配額而讓每日 10 張名額空置。畢業卡通過後保持 `graduated`；失敗則回到 `learning` 並從較後 stage 恢復，v0 可使用 Stage 5，不回 Stage 0。不要建立無限延伸的 long-term fixed intervals。

### 8.5 Review Mode and Dictation

一般 Review Mode 支援 English → Chinese 與 Chinese → English，可查看 `text`、`meaning_zh`、`example_en`、`example_zh` 及 TTS。它只供熟悉，不更新 `review_stage`；可標記 `known`。

正式通關只使用完整 `example_en` Dictation：

```text
play example_en
→ hide English sentence
→ user types full sentence
→ check answer
```

Scheduled Dictation：

- Pass：`review_stage += 1`、`last_review = today`、依下一 interval 設定 `next_review`；最後 stage 完成後設為 `graduated`；當天不再派發同一卡。
- Fail：stage 不變、`last_review = today`、`next_review = tomorrow`；不 reset，當天不再派發。

interval 表示距離上一次成功 Dictation 的天數：首次成功後依序 `+2d → +5d → +10d → +21d → +45d → +90d → +180d → graduated`。

Dictation 答案使用 deterministic normalization，之後做 normalized token sequence 的 exact comparison；禁止 fuzzy matching 與 AI grading。

Normalization 依固定順序：

1. Unicode normalize；
2. case-fold；
3. 依集中維護的 standard contraction table 展開 contraction；
4. 移除 punctuation；
5. 將 repeated whitespace 合併為單一空格並 trim。

大小寫、標點、首尾／重複空白及 contraction／expanded form 視為相同。拼字、單字增減、articles、prepositions、number、tense 與其他文法差異不得忽略；數字與英文數字詞不得互換。

對 `he's`、`she'd` 等可有多種標準展開的 contraction，normalizer 產生有限候選 token sequences；兩邊只要有一組 normalized sequence 完全相等即通過。不得因此把兩個本來都已展開但文法不同的句子視為相同。contraction table 必須集中管理並有測試。

### 8.6 Active Dictation

Active Dictation 不受每日 15/10 張限制，可持續至使用者停止。候選包含 overdue/due learning、Stage 0、graduated，優先順序為 overdue、due、unlearned，再依既有 level 權重處理同優先度項目。

- Pass：與 Scheduled Dictation 相同，具有正式排程效力；最後 stage 後畢業。本次 session 已成功的 card 不立即重複派發。
- Fail：`review_stage`、`status`、`next_review` 全部不變，不降級、不 reset、不延後、不建立 penalty；card 留在原 pool，之後仍可抽到。

------

## 9. TTS

TTS 是跨程式共用功能。

教材在建立流程完成時，使用 `edge-tts` 預先產生自然語音 MP3。此服務不需要 API key，但生成時需要網路。

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

音訊是 derived/cache data，canonical data 只有 article text 與 JSON/card data。超過 `AUDIO_CACHE_DAYS` 且未使用的音訊可清除，但不得刪除 text 或 JSON。

所有播放入口（article、vocabulary、example）必須支援 lazy regeneration：音訊存在則直接播放；不存在則重新生成、存回 cache 後播放。Old Articles 不得要求使用者先手動 Build Audio。

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
