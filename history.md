# Ultimate English Learner — Development History

> Last updated: 2026-08-28 11:09:29 +08:00 (Asia/Taipei)

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

### 2026-08-28 — Recently read articles

- Old Articles 新增 Recent Articles，記錄並直接開啟去重後最近 10 篇文章。

### 2026-08-28 13:37:06 +08:00 — Reading and navigation checkpoint

- Step 07 現行流程為不限張數的 New Cards 與按週期分層的 History Review；不再提供 Active Dictation。
- 當日 card pool 完成後仍保留，同一卡一天只推進一次；支援順序／隨機、Previous／Next、可隱藏清單與逐層 Back。
- 文章提供平滑 Typewriter 模式並記憶偏好；Old Articles 保留最近閱讀的 10 篇文章。
- `settings.json` 可同時保存 zoom 與 reading mode，兩者不互相覆蓋。
- 13 項自動測試通過。

## Known Limitations

- 背景音訊任務不跨程式啟動保存。
- `edge-tts` 生成依賴網路。
- Category 尚無 GUI 管理功能；新增分類需同步修改文件、設定與 Library 骨架。
- 未做自動 GUI 視覺測試；現有測試涵蓋資料合約、目錄讀取、設定、TTS 輸出、prompt 來源表解析與文字／timing 對齊。
