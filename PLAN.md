# Execution Plan: FreeYourHand

## 階段一：專案架構與權限引導 (Research & Scaffold)
- [ ] 初始化 Git 儲存庫與 Python 環境。
- [ ] 實作系統權限檢查機制（錄音、輔助使用）。
- [ ] 製作初次啟動的權限引導介面。

## 階段二：錄音與聲紋動畫 (UI & Audio)
- [ ] 實作基於 PyQt6 的置底透明視窗。
- [ ] 整合麥克風輸入，計算實時音量（RMS）。
- [ ] 實作能量條動畫（60fps）。
- [ ] 實作全局快捷鍵監聽（支援 Right Option 長按偵測）。

## 階段三：AI 核心與模型管理 (AI & Model Ops)
- [ ] 實作 **模型下載管理員**（UI 進度條與快取檢查）。
- [ ] 整合 `mlx-whisper` 本地辨識邏輯。
- [ ] 封裝 Gemini API 校對模組：
  - [ ] 實作 API Key 與 OAuth 授權。
  - [ ] **撰寫「精確還原」專用 Prompt**。
- [ ] 實作非同步處理隊列。

## 階段四：系統整合與輸出 (Integration)
- [ ] 實作剪貼簿寫入與 `Cmd + V` 模擬。
- [ ] 製作 Mac 選單列圖示與下拉選單。
- [ ] 實作設定視窗（快捷鍵、API 設定、Log 視圖）。

## 階段五：打包與發佈 (Packaging & QA)
- [ ] 建立全局日誌系統。
- [ ] 優化 M 晶片模型載入速度。
- [ ] **實作 `py2app` 打包腳本，生成 `FreeYourHand.app`**。
- [ ] 進行端到端測試，確保開發模式與打包模式皆可運行。
