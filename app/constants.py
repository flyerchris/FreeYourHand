"""
FreeYourHand - 全局常數與預設配置
"""

# ── App Info ──────────────────────────────────────────────
APP_NAME = "FreeYourHand"
APP_VERSION = "1.0.0"
APP_ORG = "FreeYourHand"

# ── Default Hotkey ────────────────────────────────────────
# pynput Key codes
DEFAULT_HOTKEY = "Key.alt_r"          # Right Option key
TRANSLATE_MODIFIER = "Key.shift"       # Hold Shift for translation mode

# ── Audio ─────────────────────────────────────────────────
AUDIO_SAMPLE_RATE = 16000              # Whisper expects 16kHz
AUDIO_CHANNELS = 1
AUDIO_CHUNK_SIZE = 1024
AUDIO_FORMAT_WIDTH = 2                 # 16-bit (paInt16)

# ── Whisper Models ────────────────────────────────────────
WHISPER_MODELS = {
    "tiny":        "mlx-community/whisper-tiny-mlx",
    "base":        "mlx-community/whisper-base-mlx-q4",
    "small":       "mlx-community/whisper-small-mlx",
    "medium":      "mlx-community/whisper-medium-mlx",
    "large-v3":    "mlx-community/whisper-large-v3-mlx",
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
    "distil-large-v3": "mlx-community/distil-whisper-large-v3",
}
DEFAULT_WHISPER_MODEL = "large-v3-turbo"

# ── Gemini ────────────────────────────────────────────────
DEFAULT_GEMINI_MODEL = "gemini-2.0-flash"

PROMPT_PRECISE_RESTORE = """你是一個專業的語音轉文字校對助手。請根據以下規則處理語音辨識的逐字稿：

1. **修正同音異義字**：根據上下文判斷正確的用字。
2. **補上標點符號**：加上適當的逗號、句號、問號等標點。
3. **嚴禁改寫**：不得改變使用者的用詞、語氣或表達風格。你的目標是百分之百還原使用者的真實表達，只修正明顯的辨識錯誤。
4. **不要添加任何額外的內容**：不要加上任何解釋、前言或結語。
5. **必須使用繁體中文輸出**：所有簡體中文字必須轉換為對應的繁體中文字。

請直接輸出校對後的繁體中文文字，不需任何其他說明。

逐字稿：
{transcript}"""

PROMPT_TRANSLATE = """你是一個專業的翻譯助手。請將以下語音辨識的中文逐字稿精確翻譯為英文。

規則：
1. 翻譯需精確傳達原意，不得添加或省略任何資訊。
2. 使用自然流暢的英文表達。
3. 移除語氣贅詞後再翻譯。
4. 直接輸出翻譯結果，不需任何其他說明。

逐字稿：
{transcript}"""

# ── UI ────────────────────────────────────────────────────
# Overlay window
OVERLAY_HEIGHT = 80
OVERLAY_MARGIN_BOTTOM = 40
OVERLAY_BORDER_RADIUS = 20
OVERLAY_OPACITY = 0.92

# Waveform
WAVEFORM_BAR_COUNT = 40
WAVEFORM_BAR_WIDTH = 4
WAVEFORM_BAR_GAP = 3
WAVEFORM_FPS = 60
WAVEFORM_MIN_HEIGHT = 4
WAVEFORM_MAX_HEIGHT = 50
WAVEFORM_SMOOTHING = 0.3

# Colors (RGBA)
COLOR_BG = (20, 20, 30, 235)
COLOR_WAVEFORM_START = (0, 210, 255)     # Cyan  (#00D2FF)
COLOR_WAVEFORM_END = (147, 51, 234)      # Purple (#9333EA)
COLOR_PROCESSING = (255, 180, 50)        # Amber
COLOR_SUCCESS = (34, 197, 94)            # Green
COLOR_ERROR = (239, 68, 68)              # Red
COLOR_TEXT = (255, 255, 255, 230)
COLOR_TEXT_DIM = (255, 255, 255, 128)

# ── Logging ───────────────────────────────────────────────
LOG_MAX_LINES = 5000
LOG_FILE_NAME = "freeyourhand.log"
