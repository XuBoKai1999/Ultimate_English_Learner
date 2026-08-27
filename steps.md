# English Reader — Implementation Steps

> Specification updated: 2026-08-27 17:00:22 +08:00. Step 07 requirements are not yet implemented.

## Current Status

| Step | 狀態 |
| --- | --- |
| Step 01 — Project Skeleton & Data Contract | ✅ Completed |
| Step 02 — GUI Skeleton | ✅ Completed and evolved to four Home entries |
| Step 03 — Cleaned Article Ingest | ✅ Completed |
| Step 04 — Manual AI Workflow | ✅ Completed |
| Step 05 — Card Import & Old Articles | ✅ Completed |
| Step 06 — TTS | ✅ Completed |
| Step 07 — Review System | ⏳ Next; not implemented |

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

### Stage 1

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
- Category 確定後，由 GUI 依當下年月建立 `Category/YYYY/MM/article-id/`；不得預先建立年月目錄；
- 同步建立 text 與 audio 的鏡像文章目錄；
- 將文章移至正確 Library 路徑。

### Stage 2

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

同時完成 `Old Articles` 的基本閱讀功能：

```text
Category
→ Year
→ Month
→ Article
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
library/audio/Category/YYYY/MM/article-id/
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

狀態：尚未施工。既有 Daily Learning 來源表保留，新增以下三個區塊：

| 區塊 | 功能 |
| --- | --- |
| **New Cards** | 每日首次學習 cards |
| **History Review** | scheduled spaced-repetition |
| **Active Dictation** | 不限量主動聽寫 |

### Step 07.1 — Central Configuration and Card Contract

集中定義，不得散落 hard-code：

```text
MAX_NEW_CARDS_PER_DAY = 15
MAX_HISTORY_CARDS_PER_DAY = 10
INTERVALS = [2, 5, 10, 21, 45, 90, 180]
LEVEL_WEIGHTS = {general: 4, domain: 2, specialized: 1}
OVERDUE_WEIGHTS = {due_today: 1, overdue_1_7: 2, overdue_8_30: 4, overdue_over_30: 8}
AUDIO_CACHE_DAYS = 30
```

- `status` 擴充為 `learning | graduated | known`；不得另建 learning state。
- 保留每篇文章自己的 cards；不同文章的同 vocabulary 不 deduplicate、不 merge。
- 不建立 global vocabulary index、frequency database 或額外資料庫。

### Step 07.2 — New Cards

- 每日最多 15 張；候選不足不補滿。
- 候選：`status == learning AND review_stage == 0 AND next_review <= today`。
- old backlog 定義為 article 建立時間早於目前最新 eligible article 的 Stage 0 candidates。
- old backlog 存在時至少保留 3 個名額；其餘優先最新文章；任一側不足時由另一側補位，不保留空位。
- 保留名額優先較舊 article，其餘依 article 時間由新到舊；同 article 優先度內使用既有 level 權重，最後隨機。
- Review Mode 只供熟悉，不推進 stage；正式通關使用完整例句 Dictation。

### Step 07.3 — History Review

- 每日總上限 10 張，不按 stage 分別計算。
- learning 候選：`next_review <= today AND status == learning AND review_stage > 0`。
- 依 overdue、level、最後隨機抽取，可用 `level_weight * overdue_weight`。
- overdue 權重：今天 ×1、1–7 天 ×2、8–30 天 ×4、超過 30 天 ×8。
- 通常選 9 張 learning 加 1 張 graduated；graduated 為空則由 learning 補，learning 不足則由 graduated 補，不得為維持比例留下空位。

### Step 07.4 — Review Mode and Scheduled Dictation

Review Mode 支援 English → Chinese、Chinese → English，顯示雙語內容與 TTS，但不更新 stage；可標記 `known`。

Dictation 播放 `example_en`、隱藏英文全文、要求輸入完整句子。只有成功才推進：

- Pass：stage +1、更新 `last_review`，依 `INTERVALS` 設定 `next_review`；最後 stage 後 `graduated`；當天不再派發。
- Fail：stage 不變、`last_review = today`、`next_review = tomorrow`；不 reset，當天不再派發。

排程：首次成功後 `+2d → +5d → +10d → +21d → +45d → +90d → +180d → graduated`。

答案判定只使用 deterministic normalization 後的 exact token comparison，不使用 fuzzy matching 或 AI grading：

1. Unicode normalize、case-fold；
2. 依集中 contraction table 展開 standard contractions；
3. 移除 punctuation；
4. 合併 repeated whitespace 並 trim；
5. normalized token sequence 必須完全一致。

忽略 case、punctuation、首尾／重複空白及 contraction／expanded form；不得忽略 spelling、word omission/addition、articles、prepositions、number、tense 或其他 grammar differences。數字與英文數字詞不互換。歧義 contraction 產生有限展開候選，任一 normalized sequence 完全吻合才通過；不得讓兩個不同的 expanded sentences 互相等價。contraction table 與 normalization 必須有單元測試。

graduated 通過抽查保持畢業；失敗回 `learning` 並從較後 stage 恢復，v0 可用 Stage 5，不回 Stage 0；不建立無限 long-term intervals。

### Step 07.5 — Active Dictation

- 不受每日 15/10 張限制，持續至使用者停止。
- 候選包含 overdue/due learning、Stage 0 與 graduated；優先 overdue、due、unlearned，同優先度使用既有 level 權重。
- Pass 與 Scheduled Dictation 相同並正式更新排程；本 session 已成功的 card 不立即重複。
- Fail 不改 stage、status 或 next_review，不降級、不 reset、不延後、不 penalty；之後仍可再次抽到。

### Step 07.6 — TTS Cache and Lazy Regeneration

- article text 與 JSON/card data 為 canonical；audio 只是 derived/cache data。
- 只可清除超過 `AUDIO_CACHE_DAYS` 且未使用的 audio，不得刪除 text 或 JSON。
- article、vocabulary、example 的 Play 都先檢查檔案；缺少時背景重新生成、存回 cache，再播放。
- Old Articles 不得要求使用者手動重建音訊。

### Completion Criteria

- 三個 Daily Learning 區塊可操作；
- 每日 15 張 New Cards 與總計 10 張 History Review 上限正確；
- Review Mode 不改 stage，Scheduled／Active Dictation 依規則更新；
- `learning`、`graduated`、`known` 狀態正確流轉；
- graduated long-term 抽查與失敗恢復正確；
- audio cache 只清 audio，且所有播放入口可 lazy regenerate；
- categories 來源表繼續正常顯示。

### Decisions Before Coding

New Cards backlog 配額、graduated 配額與 Dictation normalization 已於 2026-08-27 17:00:22 +08:00 確定。目前沒有必須由使用者先決定的 Step 07 規格事項。

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

除非另有指示，不要施工 `arch.md` 中列為 v0 non-goals 的功能。
