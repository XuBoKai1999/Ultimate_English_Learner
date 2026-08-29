# English Reader — Architecture v0

> Synchronized with implementation: 2026-08-28 11:38:06 +08:00.

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

### GUI code organization

GUI 採用直接的 page-function 結構，不引入 MVC、MVVM、controller 或 service layer：

```text
src/
├── gui.py                 # 啟動、主視窗、頂層導航、共用狀態與頁面切換
└── views/
    ├── daily_learning.py  # Daily Learning 與 review session
    ├── new_article.py     # New Article pipeline
    └── old_articles.py    # Library、article reader 與 vocabulary cards
```

各 view function 接收目前的 application instance 與 parent widget，因此沿用既有明確狀態與 callback。跨頁共用的縮放、導航、lazy TTS 與背景教材生成任務保留在 `gui.py`；view 不反向 import `gui.py`，避免 circular imports。

GUI 有四個主要入口：

| 頁面               | 功能                    |
| ------------------ | ----------------------- |
| **Daily Learning** | 今日複習 + 建議閱讀來源 |
| **New Article**    | 建立新教材              |
| **Old Articles**   | 閱讀與管理既有教材      |
| **Material Generation Tasks** | 查看背景音訊任務與進度 |

### 2.1 Daily Learning

顯示：

- **New Cards**：尚未完成首次 encounter 的所有 cards；
- **History Review**：依固定複習週期分層顯示的所有到期 cards；
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
→ Stage 1 full Traditional Chinese translation
→ translation_zh.md
→ Stage 2 AI analysis
→ analysis.json
→ Stage 3 card generation
→ cards.json
→ import / split
→ save
→ background TTS
```

完成後教材進入 Library。

閱讀教材由 `Old Articles` 負責。

閱讀頁的功能控制使用較小字型；Article、Vocabulary List 與卡片正文使用較大內容字型。GUI 縮放時兩級字型維持比例同步縮放。

Article 分頁頂端顯示完整音訊時間軸，下方左側為正文、右側為功能區。Vocabulary Cards 分頁左側為短音訊控制與清單，右側為卡片內容；卡片音訊不顯示時間軸。

Article 預設維持左側英文閱讀區、右側 Functions 的既有布局。存在 `translation_zh.md` 時，Functions 顯示 Show Chinese；按下後只將左側閱讀區等分為英文／繁體中文雙欄，右側功能區不移動。任一側依相對百分比同步捲動；可再次收合中文，不建立逐句 alignment data。沒有翻譯檔的舊文章維持英文單欄。

缺少 `translation_zh.md` 時，Functions 顯示 Add Chinese Translation，重用 New Article 的 translation prompt/editor；保存後只補寫現有文章並返回閱讀頁，不重跑 analysis/cards 或建立新 article unit。

### Inline selection translation

英文 Article Text widget 支援選取文字後的即時翻譯。使用者完成反白時，選取位置旁顯示較正文略小、跟隨 GUI zoom 等比例縮放的 Translate 浮動按鈕；右鍵 Translate 保留為備用入口。按下後重用單一自適應 popup，顯示所選英文及繁體中文結果。

翻譯由 `src/translation.py` 直接使用 `deep-translator` 的 `GoogleTranslator(source="en", target="zh-TW")`。網路 I/O 在 daemon thread 執行，GUI 更新透過 Tk main thread；等待中顯示 `Translating...`，失敗時在 popup 內顯示簡短錯誤。離開 Article page、按 Esc 或正常關閉視窗時清除浮動 UI。

此功能不保存翻譯、不建立 cache、history、dictionary、vocabulary entry、provider abstraction 或額外資料格式；canonical article 與全文 `translation_zh.md` 流程不受影響。

Article 閱讀區與 Functions 固定使用 4:1 layout weight；英／中 Text widgets 不得以預設字元寬度撐大容器，GUI zoom 只能縮放內容，不得改變區域比例或擠掉功能區。

切換分頁時立即停止音訊；進入 Article 分頁時立即將播放器來源重設為文章音訊，但將 MP3 解碼延後至上方播放器 Play 或文章雙擊操作，避免播放器保留上一張單字卡音訊，也避免分頁切換卡頓。

背景建置狀態由 `Material Generation Tasks` 負責；使用者可離開頁面並繼續建立其他文章。

### 2.3 Old Articles

可由按鈕切換兩種即時 Library 檢索方式：

```text
View by Category:
Category
└── Year
    └── Month
        └── Article

View by Date:
Year
└── Month
    └── Article (newest first)
```

日期模式不顯示 Category 層，只重新排列現有目錄資訊，不建立額外索引或複製文章；年份、月份與文章日期由新到舊。

文章頁提供：

- 清理後原文；
- 全文 TTS；
- 該文章的單字片語卡；
- 單字、片語與例句 TTS。
- 從既有 Categories 手動修改分類；同步移動 text/audio 鏡像並更新 analysis 與 card category；
- 經確認後永久刪除文章及其鏡像音訊。

背景音訊任務仍在 Queued／Generating 時不得修改分類或刪除，以避免路徑競態。分類目標已存在時不得覆蓋。

------

## 3. Article Unit

每篇文章視為一個學習單元。

概念上：

```text
Article Unit
├── article.md (cleaned article)
├── translation_zh.md
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

### Stage 1 — Full Article Translation

使用 `prompts/translate_article.md` 接續同一個 AI 對話，將剛完成的 cleaned English article 完整翻譯為繁體中文 Markdown。不得摘要、刪節或加入解說；GUI 驗證非空後保存為 `translation_zh.md`。

### Stage 2 — Article Analysis

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

### Stage 3 — Card Generation

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

Stage 3 產生單一批次檔案：

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

### Schedule bookkeeping

```text
status
review_stage
review_count
last_review
next_review
```

不要要求 AI 產生 schedule bookkeeping。

不同文章中的相同 vocabulary 保留為各文章自己的 card，不做跨文章 deduplication、merge、global vocabulary index 或 frequency database。重複出現視為額外 exposure。

------

## 8. Review

v0 直接使用每篇文章既有 card 與 schedule bookkeeping，不建立每日副本或另一套狀態。

### 8.1 Central Configuration

下列數值必須集中管理：

```text
INTERVALS = [2, 5, 10, 21, 45, 90, 180]
AUDIO_CACHE_DAYS = 30
```

不得散落 hard-code，不加入 FSRS、level/overdue weights、graduated pool 或 mastery scoring。

### 8.2 Time-only Schedule

派發只依 article 日期與固定週期，不依 Dictation 成功／失敗，也不判斷是否已學會。文章日期取自資料夾名稱 `YYYY-MM-DD-文章標題`。

Stage 0 為文章建立日的 New Card encounter；後續 History Review dates 從文章日固定起算：

```text
article day
→ +2d
→ +7d
→ +17d
→ +38d
→ +83d
→ +173d
→ +353d
→ schedule complete
```

這些是 `INTERVALS` 的累積日期，不因延遲完成或答案結果重新起算。沿用 `review_stage` 只記錄下一個尚未完成的 scheduled encounter；沿用 `last_review`、`next_review` 與 `review_count` 作 bookkeeping，不代表 mastery。既有 `status` 不參與候選篩選，不再加入 `known` 或 `graduated` 行為。

### 8.3 New Cards

候選為尚未完成 Stage 0 且 article date 已到的所有 cards，不設每日數量上限。開始前可選擇依 article/card 原始順序派發，或將本次候選隨機排序。完成當次 encounter 後，不論 Dictation 結果，進入固定 History Review 時間表。

當天已派發的 cards 必須留在當日 New Cards pool，離開頁面或完成一次後仍可重複練習；同一卡一天只推進一次 scheduled encounter。

### 8.4 History Review

候選為下一個固定 scheduled date 已到且尚未完成的所有 cards，不設每日數量上限。History Review 入口先按複習週期分層；每層明確顯示 interval、相對 article date 的累積天數與 card 數量，例如 `5-day interval / appeared 7 days ago / 31 cards`。使用者選定週期後，再選擇依原始順序或隨機派發。不同週期不得混在同一 session；不使用 vocabulary level、overdue weight、graduated reservation 或 long-term pool。

### 8.5 Review Mode and Dictation

點入 New Cards，或點入 History Review 的某個週期後，先選擇 English → Chinese、Chinese → English 或 Dictation，再選擇順序／隨機。三種模式使用獨立畫面，不得把控制項混在一起。

Daily Learning 的多層流程必須提供全域 Back，可逐層返回上一頁以更換順序、模式或 History Review 週期，不必回 Home 重新開始。

- English → Chinese：先顯示 `text`、`example_en`，按「顯示答案」後才顯示 `meaning_zh`、`example_zh`。
- Chinese → English：先顯示 `meaning_zh`、`example_zh`，按「顯示答案」後才顯示 `text`、`example_en`。
- 每張 card 上方提供兩個且僅兩個音訊入口：Play Word 播放 `text`，Play Example 播放 `example_en`；不得在下方重複放置播放按鈕。
- session 左側顯示本次全部 cards 的可點選摘要清單，並提供顯示／隱藏；卡片操作提供 Previous，不能只能單向 Next。

Dictation 使用完整 `example_en`：

```text
play example_en
→ hide English sentence
→ user types full sentence
→ check answer
```

Dictation 畫面只保留 Play Word、Play Example、完整句子輸入框及必要的 Previous、Next、送出／檢查操作，不顯示另外兩種 Review Mode 的控制項。

Scheduled Dictation 完成後，不論 Pass／Fail，都將該 scheduled encounter 標記完成、更新 bookkeeping，並指向自 article date 計算的下一個固定日期；card 仍留在當日 pool，但同一天不得再次推進。答案只作即時回饋，不推進或延後 mastery stage，因為沒有 mastery state。

Dictation 答案使用 deterministic normalization，之後做 normalized token sequence 的 exact comparison；禁止 fuzzy matching 與 AI grading。

Normalization 依固定順序：

1. Unicode normalize；
2. case-fold；
3. 依集中維護的 standard contraction table 展開 contraction；
4. 移除 punctuation；
5. 將 repeated whitespace 合併為單一空格並 trim。

大小寫、標點、首尾／重複空白及 contraction／expanded form 視為相同。拼字、單字增減、articles、prepositions、number、tense 與其他文法差異不得忽略；數字與英文數字詞不得互換。

對 `he's`、`she'd` 等可有多種標準展開的 contraction，normalizer 產生有限候選 token sequences；兩邊只要有一組 normalized sequence 完全相等即通過。不得因此把兩個本來都已展開但文法不同的句子視為相同。contraction table 必須集中管理並有測試。

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

文章資料夾使用 `YYYY-MM-DD-文章標題`。標題保留可讀文字，只清除作業系統不允許的字元並限制長度；同日同名依序加 `-2`、`-3`。日期同時是 Step 07 time-only schedule 的基準。

```text
library/
├── text/
│   └── Category/
│       └── YYYY/
│           └── MM/
│               └── YYYY-MM-DD-article-title/
│
└── audio/
    └── Category/
        └── YYYY/
            └── MM/
                └── YYYY-MM-DD-article-title/
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
- `translation_zh.md`：Stage 1 完整繁體中文翻譯；
- `analysis.json`：Stage 2 AI 原始輸出；
- `cards.json`：Stage 3 AI 批次原始輸出；
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

文章朗讀提供 Normal 與 Typewriter 兩種顯示模式：Normal 只確保反白行可見；Typewriter 讓目前朗讀行持續位於文章框中央。選定模式寫入 `settings.json`，後續文章及下次啟動沿用。

Article 文字區以輕量 Markdown viewer 呈現標題、粗體、斜體、inline／block code、引用及有序／無序清單；不渲染數學公式。Markdown 標記只在視覺上隱藏，底層 offset 不變，以維持 TTS timing 與雙擊跳轉。所有 Markdown fonts 使用 named fonts，跟隨 GUI zoom 等比例縮放。

Article 音訊控制在進度條旁顯示 `MM:SS / MM:SS`，分別代表目前位置與音檔總長度。

開啟 Article 時即時計算 `article.md` 的英文 word count，使用 `ENGLISH_READING_WPM = 238` 與 `ceil(words / WPM)` 估算默讀分鐘，顯示於 Article tab；不保存衍生結果、不計中文翻譯。238 WPM 依據 [Brysbaert 2019 對英文成人非小說默讀速率的 meta-analysis](https://www.sciencedirect.com/science/article/pii/S0749596X19300786)。

Old Articles 提供 Recent Articles，使用本地衍生清單記錄最近開啟的 10 篇文章；重複開啟時移到最前，超過上限移除最舊紀錄，不影響文章本體。

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
