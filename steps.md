# English Reader — Implementation Steps

> Synchronized with implementation: 2026-08-28 11:38:06 +08:00.

## Current Status

| Step | 狀態 |
| --- | --- |
| Step 01 — Project Skeleton & Data Contract | ✅ Completed |
| Step 02 — GUI Skeleton | ✅ Completed and evolved to four Home entries |
| Step 03 — Cleaned Article Ingest | ✅ Completed |
| Step 04 — Manual AI Workflow | ✅ Completed |
| Step 05 — Card Import & Old Articles | ✅ Completed |
| Step 06 — TTS | ✅ Completed |
| Step 07 — Review System | ✅ Completed |

依 `arch.md`、`categories.md` 與 `prompts/` 實作。

每次只施工指定 Step。不要提前實作後續功能。

------

## Step 01 — Project Skeleton & Data Contract

建立最小專案結構與資料格式。

完成：

- 建立必要資料夾；
- Library 僅預建 `text/<Category>/` 與 `audio/<Category>/`；不要預建年月或文章目錄；
- 定義 `analysis.json`、`cards.json` 與單張 card 的驗證格式；
- 建立基本設定與最小測試。

```text
project/
├── prompts/
├── src/
├── tests/
├── library/
│   ├── text/
│   └── audio/
├── arch.md
├── categories.md
└── steps.md
```

完成條件：

- 專案可執行；
- JSON 格式可驗證；
- 不實作 AI API 或 TTS。

------

## Step 02 — GUI Skeleton

### Current GUI module layout

GUI 骨架後續已按既有三個主要頁面保守拆分：

```text
src/gui.py
src/views/daily_learning.py
src/views/new_article.py
src/views/old_articles.py
```

`gui.py` 只協調 application startup、主視窗、導航、縮放、共用音訊工作與頁面切換。各 view 保留原有 UI、callback 與資料流程；此次拆分不改變 layout、顯示文字、review scheduling、TTS、article storage、prompts 或 card logic，也未新增 controller／model／framework。

先建立可操作的 GUI。

目前四個主要入口：

| 頁面               | 初期功能                 |
| ------------------ | ------------------------ |
| **Daily Learning** | 顯示空狀態與建議來源     |
| **New Article**    | 文章輸入區與後續流程入口 |
| **Old Articles**   | 顯示目前 Library         |
| **Material Generation Tasks** | 顯示背景教材生成任務 |

此 Step 只建立 GUI 骨架與導航。

後續 Step 直接把功能接入既有頁面，不另外建立第二套操作介面。

完成條件：

- 程式啟動後直接進入 GUI；
- 四個主要頁面可正常切換；
- GUI 可供後續 Step 持續手動測試。

------

## Step 03 — Cleaned Article Ingest

將清理後文章的匯入功能接入 `New Article`。

流程：

```text
AI-cleaned article
→ GUI input
→ article.md
```

使用者在進入 GUI 前自行使用 AI 清理文章，可參考 `prompts/clean_article.md`。

GUI 提供複製 `prompts/clean_article.md` 的按鈕，並只接收、顯示清理後文章，再保存為 `article.md`。程式不保存清理前內容，也不自行清理。

後續所有人工 AI 階段亦須由 GUI 讀取並顯示 `prompts/` 中的對應檔案，提供編輯、一鍵複製與保存功能，不得在程式碼中重複硬編碼 prompt。

編輯只影響 GUI 目前內容；不得自動修改原始 prompt。使用者按下保存時，GUI 必須再次詢問是否覆蓋原始檔案，確認後才可寫入。

分類前可先存於暫存位置。

完成條件：

- 可透過 GUI 輸入並查看清理後文章；
- 可從 GUI 複製文章清理 prompt；
- 可保存 `article.md`。

------

## Step 04 — Manual AI Workflow

將人工 AI 分析與卡片產生流程接入 `New Article`。

### Stage 1 — Full Article Translation

接續 cleaned article 的同一個 AI 對話，GUI 顯示、複製及可確認覆蓋 `prompts/translate_article.md`。使用者貼回完整繁體中文 Markdown，程式驗證非空後保存為 `translation_zh.md`。

### Stage 2 — Article Analysis

使用者將 prompt 接續貼入同一個 AI 對話；Copy 按鈕只複製 prompt，不重貼文章內容：

```text
article.md
prompts/analyze_article.md
```

使用者手動交給 AI，取得：

```text
analysis.json
```

GUI 提供匯入功能。

程式：

- 驗證 JSON；
- 讀取 Category；
- Category 確定後，由 GUI 依當下年月建立 `Category/YYYY/MM/YYYY-MM-DD-文章標題/`；標題需清除非法檔名字元，同日同名加數字 suffix；不得預先建立年月目錄；
- 同步建立 text 與 audio 的鏡像文章目錄；
- 將文章移至正確 Library 路徑。

### Stage 3 — Card Generation

再次接續同一個 AI 對話；Copy 按鈕只複製 prompt，不附加 article 或 analysis JSON：

```text
article.md
analysis.json
prompts/generate_cards.md
```

使用者手動交給 AI，取得：

```text
cards.json
```

GUI 提供匯入功能，程式驗證格式。

完成條件：

```text
article.md
analysis.json
cards.json
```

可透過 GUI 完成人工 AI pipeline。

不要呼叫 AI API。

------

## Step 05 — Card Import & Old Articles

將 `cards.json` 拆成獨立卡片：

```text
cards.json
→ validate
→ split
→ cards/card_XXX.json
```

程式加入：

```text
id
article_id
category
status
review_stage
review_count
last_review
next_review
```

保留原始 `cards.json`。

同時完成 `Old Articles` 的兩種即時 Library 瀏覽模式：

```text
View by Category:
Category
→ Year
→ Month
→ Article

View by Date:
Year
→ Month
→ Article (newest first)
```

文章頁顯示：

- article；
- 該篇全部 cards。

完成條件：

- 每個 AI item 對應一張獨立 card；
- card 可反查來源文章；
- 可從 GUI 瀏覽已完成的教材。

------

## Step 06 — TTS

加入 TTS，並直接整合至既有 GUI。

在教材建立流程完成時使用 `edge-tts` 預先生成 MP3 與 `WordBoundary` timing JSON，不得等到使用者按下播放才生成。

生成工作必須在背景執行，不阻塞 Home、New Article 或其他 GUI 操作。首頁提供第四個 `Material Generation Tasks` 入口；每篇文章顯示獨立進度條、目前狀態與失敗重試操作，並可同時追蹤多篇教材。

支援：

- 整篇文章；
- card 的 `text`；
- card 的 `example_en`。

音訊保存於：

```text
library/audio/Category/YYYY/MM/YYYY-MM-DD-article-title/
```

並與文字 Library 鏡像。

文章單元內保存：

```text
article.mp3
article.timing.json
cards/card_XXX/text.mp3
cards/card_XXX/text.timing.json
cards/card_XXX/example.mp3
cards/card_XXX/example.timing.json
```

規則：

- 文字與 JSON 為 source of truth；
- 音訊可重新生成。
- `edge-tts` 不需要 API key，但生成時需要網路；
- 使用 `pygame` 播放既有 MP3；
- 播放器支援播放／暫停、停止、重播及可互動的拖曳進度；不另顯示 Now Reading 標籤，文章框直接反白目前字詞所在行並自動捲動，雙擊文字可跳轉音訊；
- card 閱讀區直接提供 `text` 與 `example_en` 的播放控制；
- 閱讀頁採 Article／Vocabulary Cards 分頁，窄視窗或 GUI 縮放時不得隱藏播放按鈕；
- Article 頂端顯示時間軸，正文置左、功能區置右；Vocabulary Cards 左側放短音訊控制與清單、右側放卡片內容，且不顯示時間軸；
- 初次教材生成失敗可由任務頁重試；Step 07 另加入播放時缺檔的 lazy TTS regeneration。
- 背景任務目前只存在程式執行期間；關閉程式會中止尚未完成的工作。

完成條件：

- 教材完成時已產生文章與 card 音訊；
- 生成期間仍可返回 Home 或建立另一篇文章；
- 任務頁可同時顯示多篇教材的生成進度；
- `Old Articles` 中可以控制播放並追蹤朗讀位置。

------

## Step 07 — Review System

狀態：已完成。Daily Learning 來源表保留，學習區塊為：

| 區塊 | 功能 |
| --- | --- |
| **New Cards** | 所有尚未完成首次 encounter 的 cards |
| **History Review** | 按固定週期分層的所有到期 cards |

### Step 07.1 — Central Configuration and Card Contract

集中定義，不得散落 hard-code：

```text
INTERVALS = [2, 5, 10, 21, 45, 90, 180]
AUDIO_CACHE_DAYS = 30
```

- 派發只依 article date 與固定 schedule；不使用 mastery status、level/overdue weight、graduated pool 或 FSRS。
- article date 從 `YYYY-MM-DD-文章標題` 資料夾取得。
- 沿用 `review_stage`、`review_count`、`last_review`、`next_review` 只記錄 scheduled encounters，不代表是否學會；`status` 不參與候選篩選。
- 保留每篇文章自己的 cards；不同文章的同 vocabulary 不 deduplicate、不 merge。
- 不建立 global vocabulary index、frequency database 或額外資料庫。

### Step 07.2 — New Cards

- 候選為 article date 已到且尚未完成 Stage 0 的所有 cards，不設每日上限。
- session 開始前提供「按原始順序」與「隨機派發」。
- 完成 encounter 後無論 Dictation Pass／Fail，都進入固定 History Review schedule。
- 當天派發的 pool 在當日保持可見並可反覆練習；同一卡一天最多推進一次 schedule。

### Step 07.3 — History Review

- 顯示所有到期 cards，不設每日上限。
- 固定日期從 article date 累積 `INTERVALS`：article day、+2、+7、+17、+38、+83、+173、+353 天。
- History Review 入口先按週期分層；每層顯示 interval、距 article date 的累積天數與 card 數量，讓使用者知道卡片是幾天前出現的。
- 選定週期後提供「按原始順序」與「隨機派發」；不同週期不得混合。
- 延遲完成與答案結果都不得重新起算日期。

### Step 07.4 — Review Mode and Scheduled Dictation

New Cards，或 History Review 選定週期後，先選 English → Chinese、Chinese → English 或 Dictation，再選順序／隨機。三種模式使用獨立畫面：

- 全域 Back 可逐層返回順序、模式、週期或 Daily Learning 頁面，不必回 Home。

- English → Chinese：顯示英文，按「顯示答案」後才顯示中文。
- Chinese → English：顯示中文，按「顯示答案」後才顯示英文。
- 每張 card 上方只有 Play Word 與 Play Example；不得在內容下方重複播放控制。
- 左側提供可點選、可隱藏的本次 card 清單；提供 Previous 與 Next／送出流程。

Dictation 畫面只保留 Play Word、Play Example、完整句子輸入框與必要的 Previous、Next、送出／檢查操作。播放 `example_en`、隱藏英文全文、要求輸入完整句子。Pass／Fail 只提供回饋，不影響派發：

- 完成 scheduled encounter 後，不論結果都更新 bookkeeping 並指向從 article date 計算的下一固定日期。
- card 完成後仍留在當日 pool，但同一天不得再次推進；完成 +353 天 encounter 後 schedule complete。

答案判定只使用 deterministic normalization 後的 exact token comparison，不使用 fuzzy matching 或 AI grading：

1. Unicode normalize、case-fold；
2. 依集中 contraction table 展開 standard contractions；
3. 移除 punctuation；
4. 合併 repeated whitespace 並 trim；
5. normalized token sequence 必須完全一致。

忽略 case、punctuation、首尾／重複空白及 contraction／expanded form；不得忽略 spelling、word omission/addition、articles、prepositions、number、tense 或其他 grammar differences。數字與英文數字詞不互換。歧義 contraction 產生有限展開候選，任一 normalized sequence 完全吻合才通過；不得讓兩個不同的 expanded sentences 互相等價。contraction table 與 normalization 必須有單元測試。

### Step 07.5 — TTS Cache and Lazy Regeneration

- article text 與 JSON/card data 為 canonical；audio 只是 derived/cache data。
- 只可清除超過 `AUDIO_CACHE_DAYS` 且未使用的 audio，不得刪除 text 或 JSON。
- article、vocabulary、example 的 Play 都先檢查檔案；缺少時背景重新生成、存回 cache，再播放。
- Old Articles 不得要求使用者手動重建音訊。

### Completion Criteria

- New Cards 與 History Review 兩個學習區塊可操作，且不限制每日張數；
- History Review 可按週期分層，並顯示 interval、累積天數與 card 數量；
- 三種學習模式分開，且順序／隨機派發均可操作；
- 每張 card 的 Play Word 與 Play Example 可用，沒有重複播放按鈕；
- 當日 cards 完成後仍留在當日 pool，且可用 Previous 或左側清單返回；
- 所有 scheduled dates 固定由 article date 推導，Pass／Fail 不改變時間表；
- New／History 只按時間派發，不使用 mastery 或 vocabulary level；
- Dictation normalization 與 exact comparison 正確；
- audio cache 只清 audio，且所有播放入口可 lazy regenerate；
- categories 來源表繼續正常顯示。

### Decisions Before Coding

2026-08-28 改為 time-only schedule；先前的 backlog reservation、level/overdue weights、known/graduated 與 mastery-dependent progression 全部撤銷。其後再取消 New／History 每日上限與 Active Dictation，新增 History Review 週期分層、順序／隨機派發、三種模式分頁及 card 雙播放鍵。Dictation normalization 與 TTS cache 規格保留。

------

# v0 Complete

完成 Step 07 後，系統應能：

```text
找到文章
→ 手動 AI 清理
→ GUI 匯入清理後文章
→ 手動 AI 分析
→ 手動 AI 批量產生 cards
→ 程式拆分
→ GUI 閱讀
→ TTS
→ 每日排程複習
```

文章播放另提供 Normal／Typewriter 閱讀模式；Typewriter 會讓目前反白朗讀行保持在文字框中央。

載入 Article 時只計算英文 word count，依集中設定 `ENGLISH_READING_WPM = 238` 與 `ceil(words / WPM)` 即時顯示預估閱讀分鐘；不計中文、不保存衍生資料。

Old Articles 提供最近閱讀入口，持久保存去重後最近 10 篇並可直接重新開啟。

Old Articles 可切換 Category-first 與 Date-first；Date-first 不顯示 Category 層，月份內文章由新到舊。

單篇文章功能區提供 Change Category 與 Delete Article。兩者都需確認；分類變更同步 text/audio 與 card metadata，刪除同步移除 text/audio。背景 TTS 進行中或目標路徑已存在時拒絕操作。

除非另有指示，不要施工 `arch.md` 中列為 v0 non-goals 的功能。
