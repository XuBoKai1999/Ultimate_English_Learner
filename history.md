# Ultimate English Learner — Development History

> Last updated: 2026-08-29 18:50:03 +08:00 (Asia/Taipei)

本文件供新開發者或新 agent 快速接手。規格以 `arch.md` 為準，施工順序與狀態以 `steps.md` 為準；此處記錄已完成工作、設計演變與目前限制。

## Current State

- Step 01–07 已完成。
- 啟動入口：`python main.py`。
- 技術：Python、Tkinter、`edge-tts==7.2.8`、`pygame-ce==2.5.8`。
- 驗證：`python -m unittest discover -s tests -v`，目前 12 項測試。

## Implemented Milestones

### 2026-08-27 — Project and storage foundation

- 建立 `main.py`、`src/`、`tests/`、`prompts/` 與 `library/`。
- `library/text/` 與 `library/audio/` 只預建 Category；`YYYY/MM/YYYY-MM-DD-文章標題` 在文章匯入後建立。
- text/audio 採鏡像目錄；測試資料已清除，Category 骨架保留。
- 每篇文章保存 `article.md`、`analysis.json`、`cards.json` 與拆分後的 `cards/card_XXX.json`。

### 2026-08-27 — Manual conversational AI workflow

- 文章清理交給 AI，程式只接收並保存乾淨文章，不保存 raw article。
- 三個 prompt 分開保存在 `prompts/`，但可在同一 AI 對話依序使用：clean → analyze → cards。
- Copy 只複製 prompt 本身，不附加文章或上一階段 JSON。
- GUI 可編輯 prompt；只有按 Save、再確認覆蓋後才修改原檔。
- analysis/cards JSON 會驗證後再匯入；程式負責 ID、路徑、日期及 review metadata。

### 2026-08-27 — GUI and navigation

- Home 有四個入口：Daily Learning、New Article、Old Articles、Material Generation Tasks。
- GUI 支援按鈕、鍵盤與 Ctrl+滑鼠滾輪縮放；縮放值保存在 `settings.json`。
- Old Articles 即時讀取 Library 目錄，不快取檔案樹。
- 閱讀頁使用 Article／Vocabulary Cards 分頁；切換分頁會停止音訊。
- 功能字型較小，文章、Vocabulary List 與卡片正文使用 1.4 倍內容字型；整體縮放維持比例。

### 2026-08-27 — TTS and background material generation

- 參考相鄰 Versant 專案，採 `edge-tts` 預先生成 MP3；不需要 API key，但生成時需要網路。
- 同步保存 WordBoundary timing JSON；文章、card text、card example 都有獨立音訊。
- 音訊生成在 daemon 背景執行緒運作，不阻塞 Home 或 New Article。
- Material Generation Tasks 按文章顯示進度、狀態與失敗重試，可同時追蹤多篇文章。
- 任務只存在目前程式生命週期；關閉程式會終止未完成工作，尚無持久化或續傳。

### 2026-08-27 — Reading and playback interaction

- Article 頂端有播放／暫停、停止、重播及可拖曳時間軸。
- 目前朗讀位置以整個畫面顯示行反白，文章會自動捲動；不顯示 Now Reading 文字。
- 雙擊文章可跳到最接近的 WordBoundary 並開始播放。
- 切回 Article 時只登記文章音訊來源；MP3 解碼延後至 Play 或雙擊，避免分頁卡頓與誤播上一張卡片。
- Vocabulary Cards 左側為短音訊控制及清單，右側為卡片內容；卡片不顯示時間軸。

### 2026-08-27 — Daily Learning source guide

- Daily Learning 直接解析 `categories.md` 的 Default Categories 表格。
- GUI 逐項顯示 Category、範圍與建議來源；修改文件後重新進入頁面即可同步。
- 今日到期卡片、複習評分與狀態更新仍屬 Step 07。

## Important Decisions

- 不使用 Whisper 做 TTS；Whisper 是 STT，本專案語音生成使用 `edge-tts`。
- Play 優先播放 cache；缺檔時背景 lazy regenerate 後自動播放。
- 文字與 JSON 是 source of truth；audio 是可重新生成的 derived data。
- v0 不呼叫 AI API、不自動抓文章、不實作 FSRS、雲端同步或多使用者。
- 不新增 speculative service layer；目前以小型函式、JSON 與本地檔案完成流程。

## Next Work

v0 已完成；後續只處理實際使用時發現的問題，不預建下一版功能。

### 2026-08-27 16:15:22 +08:00 — Step 07 specification update

- 規格確立 Daily Learning 三區塊與每日 15/10 張上限。
- 正式學習進度只由完整例句 Dictation 推進；Review Mode 不改 stage。
- 加入固定 intervals、overdue/level weights、graduation、long-term pool 與 Active Dictation。
- 確認跨文章同 vocabulary 不合併。
- audio 定義為 30 天 derived cache，播放缺檔時必須 lazy regenerate。
- 本次只更新文件與 prompt；Python 實作尚未變更。

### 2026-08-27 17:00:22 +08:00 — Step 07 open decisions resolved

- New Cards 每日 15 張；有 old backlog 時至少保留 3 張，其餘優先最新文章，缺額互補。
- History Review 每日 10 張；通常 9 learning + 1 graduated，任一 pool 不足時由另一 pool 補位。
- Dictation 忽略 case、punctuation、空白差異與 standard contraction／expanded form。
- spelling、word 增減、articles、prepositions、number、tense 與其他文法差異仍必須完全一致。
- 判定採 deterministic normalization 後 exact comparison，不使用 fuzzy matching 或 AI grading。
- Step 07 目前沒有待使用者決定的規格阻塞；Python 實作仍未開始。

### 2026-08-28 — Review schedule simplified and article naming changed

- Step 07 改為只依 article date 與固定累積 intervals 派發，不再判斷是否學會。
- 撤銷 level/overdue weights、old backlog reservation、known、graduated、long-term pool 與依答案結果升降 stage。
- Dictation comparison、每日 15/10 上限、Active Dictation 與 TTS cache 規格保留。
- 文章目錄改為 `YYYY-MM-DD-文章標題`；非法字元會清理，同日同名加數字 suffix。
- 已修改文章匯入實作與測試；Step 07 本身仍未施工。

### 2026-08-28 11:09:29 +08:00 — Step 07 implemented

- 加入集中設定與 `src/review.py` time-only schedule。
- Daily Learning 已接入 New Cards、History Review、Review Mode 與 Active Dictation。
- Scheduled encounter 無論 Dictation 結果都按 article date 固定前進；Active Dictation 不改排程。
- Dictation 使用 deterministic contraction normalization 與 exact comparison。
- audio cache 啟動時清除 30 天未用 MP3；article、vocabulary、example 缺檔時由 Play 背景重建。
- 現有 `status` 欄位只為相容舊 cards 保留，派發器不使用。
- 12 項自動測試通過。

### 2026-08-28 11:38:06 +08:00 — Step 07 card flow simplified

- 移除 Active Dictation 與 New／History 每日張數上限。
- History Review 改為先按固定週期分層，顯示 interval、article age 與 card 數量。
- New／History 接著分別選擇 English → Chinese、Chinese → English 或 Dictation，再選原始順序／隨機派發。
- card 畫面只保留上方 Play Word 與 Play Example；兩種翻譯模式僅顯示答案，Dictation 僅保留雙播放鍵與輸入框。
- 12 項自動測試通過。

### 2026-08-28 — Daily card sessions retained

- 已完成的 card 在當天仍保留於原 New／History pool，可反覆練習；同一天不重複推進 schedule。
- 學習頁加入 Previous 與可點選、可隱藏的左側 card 摘要清單。
- 12 項自動測試通過。

### 2026-08-28 — Review navigation improved

- Dictation 加入 Next。
- 全域工具列加入 Back，可逐層返回 Daily Learning 的週期、模式與排序頁。

### 2026-08-28 — Article typewriter mode

- 文章朗讀新增 Normal／Typewriter 切換；Typewriter 讓目前反白行平滑移動並持續置中，同一行內不重複刷新反白；選擇會跨文章、跨啟動保存。
- 修正 Typewriter 第一行 display-line count 為零時造成 callback 中止；反白改以文字框實際 tag 為準，Replay／seek 會立即重新同步 timing，單次 callback 也不再永久停止播放器更新。
- Article 播放器新增目前時間／總時長顯示，並與播放及 seek 同步。
- Article 文字區改為保留 timing offsets 的輕量 Markdown viewer；支援標題、基本 inline 樣式、code、引用與清單，並跟隨 GUI zoom。

### 2026-08-28 — Recently read articles

- Old Articles 新增 Recent Articles，記錄並直接開啟去重後最近 10 篇文章。
- 單篇文章新增確認式 Change Category／Delete Article；同步處理 text/audio 鏡像與 category metadata，並禁止在背景 TTS 進行中操作。
- Old Articles 新增 View by Date／View by Category；日期模式為 `Year → Month → Article`，不再插入 Category 層，月份內由新到舊。

### 2026-08-28 — Full article translation stage

- New Article 在清理與分析之間新增連續式 AI 全文繁體中文翻譯 prompt。
- 翻譯保存為 `translation_zh.md`；analysis/cards 順延為 Stage 2/3。Old Articles 維持原布局，按 Show Chinese 後才將左側閱讀框等分為同步捲動的英／中雙欄。
- 修正 zoom 時 Text/Combobox requested width 撐壞布局；Article/Functions 固定 4:1，英／中欄可隨容器縮放。
- 缺少全文翻譯的 Old Article 可由 Add Chinese Translation 進入既有翻譯 prompt/editor，補寫後直接返回文章。
- 修正英／中雙向捲動在文章中段因長度換算誤差形成 callback 回授、造成閱讀框跳動閃爍；中文收合時停用同步，展開時以 event-loop lock 防止反推。

### 2026-08-28 13:37:06 +08:00 — Reading and navigation checkpoint

- Step 07 現行流程為不限張數的 New Cards 與按週期分層的 History Review；不再提供 Active Dictation。
- 當日 card pool 完成後仍保留，同一卡一天只推進一次；支援順序／隨機、Previous／Next、可隱藏清單與逐層 Back。
- 文章提供平滑 Typewriter 模式並記憶偏好；Old Articles 保留最近閱讀的 10 篇文章。
- `settings.json` 可同時保存 zoom 與 reading mode，兩者不互相覆蓋。
- 13 項自動測試通過。

### 2026-08-28 14:58:12 +08:00 — Translation and article management checkpoint

- New Article 已加入完整繁體中文翻譯階段；Old Articles 可補寫缺少的翻譯。
- Article 維持 4:1 閱讀／功能布局；Show Chinese 只在左側閱讀區展開同步捲動的英／中雙欄。
- 修正 zoom requested width 與英／中捲動 callback 回授造成的擠壓、跳動及閃爍。
- Old Articles 支援最近閱讀、修改 Category 與確認式永久刪除。
- Old Articles 可切換 Category-first 與 `Year → Month → Article` 日期檢索；日期模式不顯示 Category，文章由新到舊。
- 17 項自動測試通過。

### 2026-08-29 16:51:01 +08:00 — Article reader layout and reading estimate

- 移除文章頁重複的內部返回／標題列，縮小外距，並將 Audio buttons、進度條與時間合併為單一橫列，增加閱讀器垂直高度。
- Article tab 新增英文閱讀時間估算；載入時依 238 WPM 計算，不處理中文或保存衍生資料。
- 17 項自動測試通過。

### 2026-08-29 17:09:50 +08:00 — GUI modules refactored

- 將 1,289 行的 `src/gui.py` 保守拆分為 `views/daily_learning.py`、`views/new_article.py` 與 `views/old_articles.py`；`gui.py` 縮減至約 254 行。
- `gui.py` 保留 application startup、主視窗、頂層導航、縮放、共用 lazy TTS、背景教材生成任務與頁面切換。
- 頁面實作以既有 function 直接綁定 application，未加入 MVC／MVVM、controller、service、model、framework 或新 dependency。
- 此次僅搬移既有程式碼；GUI layout、文字、資料格式、review scheduling、TTS、article storage、prompts 與 card logic 均未更動。
- 既有 17 項測試全部通過；主視窗與三個頁面 builder 的啟動 smoke test 通過。

### 2026-08-29 17:16:55 +08:00 — Post-refactor GUI regression fix

- 修正 `src/views/daily_learning.py` 搬移時遺漏的 `AudioPlayer` import；否則進入 Review Session 時會發生 `NameError`。
- 修正 `src/views/new_article.py` 搬移時遺漏的 `Path` import；否則 existing-article translation flow 會發生 `NameError`。
- Ruff undefined-name 檢查、完整 17 項測試、`src` compile/import，以及指定導航與 workflow smoke checks 全部通過。
- 未修改 GUI layout、功能、資料格式或架構。

### 2026-08-29 17:42:45 +08:00 — Inline article translation

- 新增 `deep-translator==1.11.4` 與 `src/translation.py`，直接使用 Google Translate 將英文翻為繁體中文。
- Article reader 可反白單字、片語、句子或較長文字；完成選取後只顯示 Translate 浮動按鈕，不保留右鍵入口。
- 浮動按鈕使用比正文稍小的 GUI 字型與字元尺寸，跟隨全域 zoom 等比例調整；translation popup 不再使用固定像素 geometry，避免 160% 時中文遭裁切。
- 翻譯請求在背景 thread 執行；單一 popup 會重用，支援等待、錯誤、點擊外部關閉、Esc、正常關閉及離開頁面清理。
- 實際 Google 翻譯已驗證單字、片語、完整句、apostrophe／標點及 947 字元選取；popup 重用與失敗處理 smoke check 通過，完整測試為 18 項。

### 2026-08-29 18:10:40 +08:00 — Lightweight dictionary lookup

- Inline translation 延伸為三來源 lookup：`deep-translator` 翻譯、Datamuse 拼字建議、Free Dictionary API 英文 dictionary data；未新增 dependency 或 API key。
- 單字支援外圍標點、明示 `Did you mean` correction、修正後翻譯／查字；片語與完整句只翻譯。
- Dictionary 顯示最多四組詞性、每組最多兩條定義、API 提供的例句及最多六個同義詞，保持 popup 精簡。
- 三來源失敗互不影響；快速連續 lookup 只呈現最新 request。popup 外點擊關閉，內部選取／點擊不會提前關閉。
- 實際服務驗證：`eliable` 得到 `reliable` 建議、`run` 得到四組詞性與精簡 dictionary data；Free Dictionary API 對部分詞彙曾逾時，graceful degradation 正常。
- 完整測試增至 23 項，compile/import 與 GUI popup smoke checks 通過。

### 2026-08-29 18:17:01 +08:00 — Dictionary popup layout refined

- 英文原文區由固定五行改為依選取內容自動使用 1–6 行；單字只佔一行。
- Dictionary 結果改用結構化 Text tags 排版，分離詞頭、詞性、定義、例句與同義詞，並加入縮排、間距、斜體及垂直捲軸。
- 160% GUI zoom layout smoke check、23 項測試及 compile/import check 通過。

### 2026-08-29 18:23:43 +08:00 — Partial-word lookup latency fixed

- 將翻譯、原詞 dictionary、Datamuse suggestion 及修正詞 lookup 改為重疊執行，避免殘缺詞依序累加多個 timeout。
- Datamuse／Dictionary timeout 由 8 秒縮至 4 秒；`microcontrolle` 實測約 4.5 秒取得 `microcontroller` 建議及修正後中文。
- Free Dictionary API 本輪對 `microcontroller` 的 `en`／`en_US` 均逾時；UI 改為明示 dictionary unavailable，服務恢復時仍自動顯示詞性、定義、例句與同義詞。
- 23 項測試及 compile/import check 通過。

### 2026-08-29 18:28:45 +08:00 — Lookup capped at two seconds

- Datamuse／Dictionary HTTP timeout 由 4 秒降為 1.5 秒，整體 lookup 設定 2 秒 display deadline。
- deadline 後不再等待仍在執行的外部請求，立即顯示期限內取得的翻譯、建議與 dictionary data。
- `microcontrolle` 實測 1.99 秒返回 `microcontroller` 建議與中文；未及回應的 dictionary 正確降級為 unavailable。
- 23 項測試及 compile/import check 通過。

### 2026-08-29 18:38:09 +08:00 — Dictionary outcomes separated

- Dictionary lookup result 新增 `found`、`not_found`、`timeout`、`unavailable` 明確狀態。
- 只有 API 明確回 HTTP 404 才顯示沒有詞條；request timeout 或兩秒 deadline 顯示逾時，其他服務錯誤顯示 service unavailable。
- 23 項測試及 compile/import check 通過。

### 2026-08-29 18:43:42 +08:00 — Lookup now updates progressively

- 移除將整份結果限制在兩秒 deadline 的錯誤做法；Google 翻譯完成即先更新 popup，不再等待 Dictionary。
- Datamuse suggestion 與修正後翻譯為第二階段，Free Dictionary 為最後階段；字典等待中顯示 continuing 狀態。
- `microcontroller` 實測 Google 翻譯在 0.33 秒先顯示，Dictionary 後續結果不會清除既有翻譯。
- 23 項測試及 compile/import check 通過。

### 2026-08-29 18:48:30 +08:00 — Editable lookup query

- Translation popup 的 English 欄位改為可編輯，允許直接補全殘缺單字或改寫查詢。
- 按 Enter 會重用同一 popup 重新搜尋，不插入換行；request id 保護仍避免舊結果覆蓋新查詢。
- Tk Return-key smoke check、23 項測試及 compile/import check 通過。

## Known Limitations


- 背景音訊任務不跨程式啟動保存。
- `edge-tts` 生成依賴網路。
- Category 尚無 GUI 管理功能；新增分類需同步修改文件、設定與 Library 骨架。
- 未做自動 GUI 視覺測試；現有測試涵蓋資料合約、目錄讀取、設定、TTS 輸出、prompt 來源表解析與文字／timing 對齊。
