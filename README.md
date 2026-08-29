# Ultimate English Learner

一個使用真實英文文章建立個人教材的本地桌面程式。文章清理、分析與單字卡內容由使用者在同一個 AI 對話中手動完成；程式負責驗證、整理、儲存、背景生成語音及閱讀播放。

## Current Status

- Step 01–07 已完成。
- 最後同步：2026-08-29 17:09:50 +08:00。

## Features

- 四個首頁入口：Daily Learning、New Article、Old Articles、Material Generation Tasks。
- 四段連續式 AI prompts：文章清理、全文翻譯、文章分析、單字卡生成。
- prompt 可在 GUI 編輯、複製，並在確認後覆蓋原檔。
- 即時 Library 檔案瀏覽器。
- Old Articles 提供最近閱讀清單，保留最近開啟的 10 篇文章。
- Old Articles 可切換 `Category → Year → Month → Article` 或 `Year → Month → Article`；日期模式不顯示 Category，文章由新到舊。
- Old Articles 可經確認後修改文章分類或永久刪除文章，並同步處理鏡像音訊與卡片 metadata。
- `edge-tts` 背景生成文章、單字／片語及例句 MP3。
- 多篇教材生成進度與失敗重試。
- 文章時間軸、拖曳跳轉、雙擊文字跳轉、朗讀行反白及自動捲動。
- Article 播放器顯示目前播放時間與音檔總時長。
- Article 分頁依英文詞數與 238 WPM 即時計算約需閱讀分鐘，不保存額外資料。
- 文章朗讀可切換 Normal／Typewriter；Typewriter 讓目前朗讀行保持在閱讀框中央。
- Article 以可縮放的 Markdown 樣式顯示標題、基本文字格式、程式碼、引用與清單；不處理數學公式。
- 有全文翻譯時，可按 Show Chinese 將原英文閱讀框展開為同步捲動的英／中雙欄。
- 缺少全文翻譯時，可從 Article Functions 進入既有翻譯 prompt/editor 補寫。
- Vocabulary Cards 獨立的短音訊控制與卡片閱讀介面。
- GUI 整體縮放與閱讀模式設定記憶。
- Daily Learning 直接顯示 `categories.md` 定義的分類、範圍與建議來源。
- Daily Learning 提供不限張數的 New Cards，以及按複習週期分層的 History Review。
- 卡片可選 English → Chinese、Chinese → English 或 Dictation，以及原始順序／隨機派發。
- 學習頁提供雙播放鍵、Previous／Next、可隱藏卡片清單及逐層 Back 導覽。
- time-only schedule、deterministic Dictation comparison 與 lazy TTS regeneration。

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

## GUI Source Layout

```text
src/
├── gui.py
└── views/
    ├── daily_learning.py
    ├── new_article.py
    └── old_articles.py
```

`gui.py` 負責程式啟動、主視窗、導航、共用狀態與頁面切換；三個 `views` 模組分別保存對應頁面的 UI 與頁面專屬互動。共用的縮放、lazy TTS 及背景教材生成任務仍由 `gui.py` 管理。

## Article Workflow

1. 將原始文章交給 AI，複製 GUI 顯示的 cleaning prompt。
2. 將 AI 清理後的文章貼回 New Article 並保存。
3. 在同一個 AI 對話貼上 translation prompt，將完整繁體中文 Markdown 貼回 GUI。
4. 繼續貼上 analysis prompt，再將 JSON 貼回 GUI。
5. 繼續貼上 card generation prompt，再將 cards JSON 貼回 GUI。
6. 程式拆分 cards，並在背景生成所有文章及卡片音訊。
7. 可返回 Home、繼續建立另一篇文章，或在 Material Generation Tasks 查看進度。

Copy 按鈕只複製 prompt，不會附加文章或上一階段 JSON。

## Storage

```text
library/
├── drafts/
├── text/Category/YYYY/MM/YYYY-MM-DD-article-title/
│   ├── article.md
│   ├── translation_zh.md
│   ├── analysis.json
│   ├── cards.json
│   └── cards/card_XXX.json
└── audio/Category/YYYY/MM/YYYY-MM-DD-article-title/
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
- Category 尚無 GUI 管理功能。

## Step 07 Review System

- Daily Learning 分為 New Cards 與按週期分層的 History Review，兩者都不設每日張數上限。
- 每個週期顯示 interval、文章距今天數與卡片數量；選定後可選三種學習模式及原始順序／隨機派發。
- 當天派發的 cards 完成後仍保留於當日 pool，可用 Previous、Next 或可隱藏的左側清單反覆練習；同一卡一天只推進一次 schedule。
- 卡片提供 Play Word 與 Play Example；全域 Back 可逐層更換排序、模式或週期。
- 派發只依 article date 與固定累積週期，不判斷是否學會，也不使用 level／overdue 權重或 graduated pool。
- Dictation Pass／Fail 只提供回饋，不改變固定時間表。
- Dictation 使用 deterministic normalization 後精確比較，不使用 fuzzy matching 或 AI grading。
- 音訊採 30 天 cache，缺檔時由播放操作 lazy regenerate。

詳細規則見 [Implementation Steps](steps.md#step-07--review-system)。
