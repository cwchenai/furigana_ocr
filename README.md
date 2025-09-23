# Furigana OCR Overlay

Furigana OCR Overlay 是一個桌面小工具，會定期擷取螢幕上指定區域的畫面，
並利用 OCR、斷詞與字典查詢在原畫面上方疊加顯示假名與詞義提示。
程式以模組化架構設計，方便日後維護與擴充。

## 主要功能

- 桌面工具列常駐的主視窗，可開始/停止 OCR 任務、調整頻率、強制觸發與結束程式。
- 全螢幕框選工具，選擇欲解析的畫面區域。
- 以 pytesseract 或 PaddleOCR 進行日文 OCR，搭配 fugashi 斷詞、pykakasi 產生振假名、jamdict 查詢字典。
- 透明 overlay 顯示假名與字詞，滑鼠移到單字時即彈出字典解釋。
- overlay 僅在單字上接收滑鼠事件，不會阻擋背景程式操作。
- 系統工具列整合，支援右鍵選單的開始/停止與結束指令。

## 架構概覽

```
src/
└── furigana_ocr/
    ├── app.py                # Qt 應用程式進入點
    ├── config.py             # 統一的設定模型
    ├── core/                 # 核心服務：截圖、OCR、斷詞、字典、資料模型
    ├── services/             # Pipeline 將核心服務串成流程
    ├── ui/                   # Qt 介面元件：主視窗、overlay、系統工具列、範圍選取
    └── utils/                # 共用工具（計時器、幾何處理）
```

工作流程如下：

1. 主視窗觸發 `RegionSelector` 讓使用者框選範圍。
2. `ProcessingPipeline` 依頻率由 `ScreenCapture` 擷取影像，交給設定中的 OCR 引擎。
3. OCR 結果經 `Tokenizer` 斷詞、`FuriganaGenerator` 產生假名、`DictionaryLookup` 查詢字典。
4. 產生的 `TokenAnnotation` 透過 `OverlayWindow` 在原畫面上方標註，滑鼠 hover 顯示字典內容。

## 安裝與執行

1. 安裝系統相依項目：
   - [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) 與日文語言包（使用 Tesseract 引擎時需要）。
   - 建議安裝 `unidic-lite` 以供 fugashi 使用。
2. 安裝 Python 相依套件：

```bash
pip install .
```

3. 以指令啟動：

```bash
python -m furigana_ocr
# 或
furigana-ocr
```

首次按下「開始」時會出現框選畫面。選取後程式會依照設定頻率自動更新；
可透過「強制觸發」按鈕立即刷新並重設計時器。
主視窗縮到工具列時，可從右鍵選單重新顯示、開始/停止或結束程式。

## 後續規劃

- 針對多螢幕與高 DPI 情境的更完整支援。
- 以背景工作緒列排程避免大量併發時的資源競爭。
- 自訂字典資料來源與顯示樣式。
