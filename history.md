# Ultimate English Learner — Development History

> Last updated: 2026-08-27 15:13:01 +08:00 (Asia/Taipei)

本文件供新開發者或新 agent 快速接手。規格以 `arch.md` 為準，施工順序與狀態以 `steps.md` 為準；此處記錄已完成工作、設計演變與目前限制。

## Current State

- Step 01–06 已完成。
- Step 07（Daily Learning 複習系統）尚未施工。
- 啟動入口：`python main.py`。
- 技術：Python、Tkinter、`edge-tts==7.2.8`、`pygame-ce==2.5.8`。
- 驗證：`python -m unittest discover -s tests -v`，目前 8 項測試。

## Implemented Milestones

### 2026-08-27 — Project and storage foundation

- 建立 `main.py`、`src/`、`tests/`、`prompts/` 與 `library/`。
- `library/text/` 與 `library/audio/` 只預建 Category；`YYYY/MM/article-id` 在文章匯入後建立。
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
- 不在播放時臨時生成音訊；Play 只播放已生成檔案。
- 文字與 JSON 是 source of truth；audio 是可重新生成的 derived data。
- v0 不呼叫 AI API、不自動抓文章、不實作 FSRS、雲端同步或多使用者。
- 不新增 speculative service layer；目前以小型函式、JSON 與本地檔案完成流程。

## Next Work

依 `steps.md` 執行 Step 07：

1. 掃描 `cards/card_XXX.json`，找出 `status == learning` 且 `next_review <= today` 的卡片。
2. 在 Daily Learning 顯示到期卡片並提供最小複習操作。
3. 更新 `review_stage`、`review_count`、`last_review`、`next_review`。
4. 支援標記 `known`，使卡片退出一般排程。

## Known Limitations

- 背景音訊任務不跨程式啟動保存。
- `edge-tts` 生成依賴網路。
- Category 尚無 GUI 管理功能；新增分類需同步修改文件、設定與 Library 骨架。
- Daily Learning 尚未有 spaced-repetition 行為。
- 未做自動 GUI 視覺測試；現有測試涵蓋資料合約、目錄讀取、設定、TTS 輸出、prompt 來源表解析與文字／timing 對齊。

