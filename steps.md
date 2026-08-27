# English Reader — Implementation Steps

> Last synchronized with implementation: 2026-08-27 15:13:01 +08:00

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
- 若生成失敗，只能由明確的 Build Audio 操作重試，不可隱藏在 Play 操作內。
- 背景任務目前只存在程式執行期間；關閉程式會中止尚未完成的工作。

完成條件：

- 教材完成時已產生文章與 card 音訊；
- 生成期間仍可返回 Home 或建立另一篇文章；
- 任務頁可同時顯示多篇教材的生成進度；
- `Old Articles` 中可以控制播放並追蹤朗讀位置。

------

## Step 07 — Review System

實作最小 spaced repetition，並接入 `Daily Learning`。

使用集中設定的固定複習間隔。

卡片至少支援：

```text
learning
known
```

到期條件：

```text
next_review <= today
AND status == learning
```

完成一次複習後更新：

```text
review_stage
review_count
last_review
next_review
```

標記 `known` 後退出一般排程。

`Daily Learning` 已先完成 `categories.md` Default Categories 表格的即時解析與顯示；本 Step 尚需加入到期卡片與複習操作。

完成條件：

- GUI 顯示今日到期 cards；
- 可完成複習並更新狀態；
- 可標記已知；
- 可查看建議閱讀來源。

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
