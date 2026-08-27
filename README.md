# Ultimate English Learner

一個使用真實英文文章建立個人教材的本地桌面程式。文章清理、分析與單字卡內容由使用者在同一個 AI 對話中手動完成；程式負責驗證、整理、儲存、背景生成語音及閱讀播放。

## Current Status

- Step 01–06 已完成。
- Step 07（Daily Learning 間隔複習）尚未實作。
- Step 07 規格已於 2026-08-27 17:00:22 +08:00 完成決策，但尚未實作。

## Features

- 四個首頁入口：Daily Learning、New Article、Old Articles、Material Generation Tasks。
- 三段連續式 AI prompts：文章清理、文章分析、單字卡生成。
- prompt 可在 GUI 編輯、複製，並在確認後覆蓋原檔。
- 即時 Library 檔案瀏覽器。
- `edge-tts` 背景生成文章、單字／片語及例句 MP3。
- 多篇教材生成進度與失敗重試。
- 文章時間軸、拖曳跳轉、雙擊文字跳轉、朗讀行反白及自動捲動。
- Vocabulary Cards 獨立的短音訊控制與卡片閱讀介面。
- GUI 整體縮放與設定記憶。
- Daily Learning 直接顯示 `categories.md` 定義的分類、範圍與建議來源。

## Requirements

- Python 3.14（目前測試版本）
- 生成 TTS 時需要網路
- 播放音訊需要可用的系統音訊裝置

安裝 dependencies：

```powershell
python -m pip install -r requirements.txt
```

## Run

```powershell
python main.py
```

## Article Workflow

1. 將原始文章交給 AI，複製 GUI 顯示的 cleaning prompt。
2. 將 AI 清理後的文章貼回 New Article 並保存。
3. 在同一個 AI 對話貼上 analysis prompt，再將 JSON 貼回 GUI。
4. 繼續貼上 card generation prompt，再將 cards JSON 貼回 GUI。
5. 程式拆分 cards，並在背景生成所有文章及卡片音訊。
6. 可返回 Home、繼續建立另一篇文章，或在 Material Generation Tasks 查看進度。

Copy 按鈕只複製 prompt，不會附加文章或上一階段 JSON。

## Storage

```text
library/
├── drafts/
├── text/Category/YYYY/MM/article-id/
│   ├── article.md
│   ├── analysis.json
│   ├── cards.json
│   └── cards/card_XXX.json
└── audio/Category/YYYY/MM/article-id/
    ├── article.mp3
    ├── article.timing.json
    └── cards/card_XXX/
        ├── text.mp3
        ├── text.timing.json
        ├── example.mp3
        └── example.timing.json
```

文字與 JSON 是 source of truth；音訊可重新生成。

## Tests

```powershell
python -m unittest discover -s tests -v
```

## Documentation

- [Architecture](arch.md)：完整設計與邊界。
- [Implementation Steps](steps.md)：施工順序與目前進度。
- [Development History](history.md)：歷次修改、決策、限制與接手資訊。
- [Categories and Sources](categories.md)：文章分類與建議來源。

## Known Limitations

- AI 操作目前為人工流程，沒有串接 AI API。
- 背景音訊任務只存在目前程式執行期間；關閉程式會終止未完成工作。
- Daily Learning 尚未實作到期卡片與間隔複習。
- Category 尚無 GUI 管理功能。

## Planned Step 07

- Daily Learning 分為 New Cards、History Review、Active Dictation。
- 每日上限：15 張新卡、10 張歷史複習卡。
- New Cards 為 old backlog 保留至少 3 張；History Review 通常保留 1 張 graduated card，候選不足時互相補位。
- 完整例句 Dictation 才推進固定間隔排程。
- Dictation 使用 deterministic normalization 後精確比較，不使用 fuzzy matching 或 AI grading。
- 狀態支援 `learning`、`graduated`、`known`。
- 音訊採 30 天 cache，缺檔時由播放操作 lazy regenerate。

詳細規則見 [Implementation Steps](steps.md#step-07--review-system)。目前沒有必須先由使用者決定的 Step 07 規格事項。
