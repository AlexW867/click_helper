# Click 小幫手

![Python](https://img.shields.io/badge/Python-3.14+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg)

阿就是個錄製滑鼠點擊動作的小幫手

## 功能

* 錄製滑鼠動作 F10
* 視覺化編輯器
* 可程式化流程控制，可設置或新增等待時間與迴圈節點
* 支援匯出/匯入為 JSON 格式，方便備份與管理。
* 系統防鎖定: 執行期間自動防止系統進入睡眠模式（Windows: SetThreadExecutionState / macOS: caffeinate），確保自動化任務不中斷。

## 🛠️ 安裝說明

懶懶的請下載直接使用 https://github.com/AlexW867/click_helper/releases/latest 裡面的 exe 檔

--- 以上麻瓜，以下宅宅 ---

## 使用原始碼跑的環境需求
* Windows 10/11 或 macOS
* Python 3.14 或以上版本
* [uv](https://docs.astral.sh/uv/getting-started/installation/)

### 安裝步驟
1. **複製儲存庫**:
   ```bash
   git clone https://github.com/AlexW867/click_helper
   cd click_helper
   ```

2. **安裝依賴套件**:
   ```bash
   uv sync
   ```

3. **macOS 額外步驟**:
   ```bash
   brew install python-tk@3.14
   ```
   首次執行時需到 **系統設定 > 隱私權與安全性 > 輔助使用** 允許終端機的存取權限。

4. **啟動程式**:
   ```bash
   uv run click_helper.py
   ```

## 打包

Windows (exe):
```bash
uv run pyinstaller --onefile --windowed --add-data "click_helper.ico;." --icon "click_helper.ico" click_helper.py
```

macOS (app):
```bash
uv run pyinstaller --onefile --windowed --add-data "click_helper.ico:." --icon "click_helper.ico" click_helper.py
```

## 使用方法

| 熱鍵 | 功能 |
| :--- | :--- |
| **F10** | **開始 / 停止錄製** (自動最小化視窗) |
| **F11** | **停止播放** (緊急中斷) |
| **Delete** | 刪除選中的節點 |
| **滑鼠右鍵** | 開啟編輯選單 |
| **滑鼠雙擊** | 編輯節點屬性 (次數、連點、秒數) |


---
*本程式僅供學習與自動化輔助使用，請勿用於惡意用途。*
