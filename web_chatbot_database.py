import streamlit as st
import google.generativeai as genai
from gtts import gTTS
from PIL import Image
import sqlite3
import pandas as pd
from datetime import datetime
import uuid
import io
import base64

# --- 1. 資料庫設定 ---
DB_NAME = "chat_history.db"

# 使用 st.cache_resource 替代 st.singleton 來管理單一連線
@st.cache_resource
def get_db_connection():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            timestamp DATETIME NOT NULL
        )
    """)
    conn.commit()

def log_message_to_db(session_id, role, content):
    conn = get_db_connection()
    cursor = conn.cursor()
    timestamp = datetime.now()
    cursor.execute(
        "INSERT INTO conversations (session_id, role, content, timestamp) VALUES (?, ?, ?, ?)",
        (session_id, role, content, timestamp)
    )
    conn.commit()

# --- 2. 網頁基礎配置 ---
st.set_page_config(
    page_title="AI 助理 (含紀錄下載)",
    page_icon="💾",
    layout="centered"
)

# --- 語音生成函數 ---
def text_to_speech_autoplay(text: str, language_tld: str):
    try:
        tts = gTTS(text=text, lang='zh-TW', tld=language_tld, slow=False)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        audio_base64 = base64.b64encode(audio_fp.read()).decode('utf-8')
        audio_html = f'<audio autoplay><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg"></audio>'
        st.components.v1.html(audio_html, height=0)
    except Exception as e:
        st.error(f"語音生成失敗：{e}")


# --- 3. 側邊欄 (Sidebar) ---
st.sidebar.header("⚙️ 核心設定")

# API Key, 角色設定, 模型選擇, 語音設定 (與之前相同)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    api_key = None
if not api_key:
    st.sidebar.warning("尚未設定 API Key！請在 Streamlit Cloud Secrets 中設定。")
    api_key = st.sidebar.text_input("或在此臨時輸入您的 Google API Key：", type="password")

default_persona = "你是一位知識淵博、觀察力敏銳的 AI 助理。"
st.sidebar.subheader("🎭 角色特性設定")
persona_prompt = st.sidebar.text_area("請輸入 AI 的角色描述 (System Prompt)：", value=default_persona, height=200)

model_name = st.sidebar.selectbox("選擇模型 (Vision Pro 支援圖片/攝影)", ("gemini-1.5-pro-latest", "gemini-1.5-flash-latest"))

st.sidebar.subheader("🔊 語音設定")
tts_enabled = st.sidebar.toggle("啟用/關閉語音輸出", value=True)
voice_options = {"台灣 - 標準女聲": "com.tw", "美國 - 英語女聲": "us", "英國 - 英語女聲": "co.uk"}
selected_voice_name = st.sidebar.selectbox("選擇語音", list(voice_options.keys()))
selected_voice_tld = voice_options[selected_voice_name]


# --- (更新) 資料庫管理區塊 ---
st.sidebar.subheader("🗂️ 對話紀錄資料庫")
if st.sidebar.button("顯示所有紀錄"):
    try:
        conn = get_db_connection()
        df = pd.read_sql_query("SELECT * FROM conversations ORDER BY timestamp DESC", conn)
        st.sidebar.dataframe(df)
    except Exception as e:
        st.sidebar.error(f"讀取資料庫失敗: {e}")

# (新增) 下載紀錄按鈕
try:
    conn = get_db_connection()
    db_df = pd.read_sql_query("SELECT * FROM conversations ORDER BY timestamp ASC", conn)
    # 將 DataFrame 轉換為 CSV 格式 (存在記憶體中)
    # index=False 避免將 pandas 的索引寫入檔案
    # encoding='utf-8-sig' 確保中文字在 Excel 中正常顯示
    csv = db_df.to_csv(index=False).encode('utf-8-sig')
    
    st.sidebar.download_button(
        label="📥 下載對話紀錄 (CSV)",
        data=csv,
        file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv",
    )
except Exception as e:
    st.sidebar.error(f"準備下載檔失敗: {e}")


# --- 4. 主應用程式介面 ---
st.title("💾 AI 助理 (含紀錄下載)")
st.caption("所有對話都將被記錄在 SQLite 資料庫中")

# 應用程式啟動時初始化
init_db()

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

# --- 後續程式碼與之前版本完全相同 ---

# 5. 初始化模型與對話
chat = None
if not api_key:
    st.error("⚠️ 請在左側設定您的 Google API Key。")
elif not persona_prompt.strip():
    st.error("⚠️ 角色的特性設定不能為空！")
else:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name, system_instruction=persona_prompt)
        chat = model.start_chat(history=[])
        if "messages" not in st.session_state:
             st.success("模型已成功載入！")
    except Exception as e:
        st.error(f"模型或 API Key 載入失敗：{e}")

# 6. 對話歷史記錄管理
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        if "image" in message:
            st.image(message["image"], width=200)
        st.markdown(message["content"])

# 7. 圖片/攝影上傳與管理
st.subheader("圖片/攝影輸入")
tab1, tab2 = st.tabs(["📁 檔案上傳", "📷 攝影機拍照"])
with tab1:
    uploaded_image = st.file_uploader("上傳圖片檔案...", type=["jpg", "jpeg", "png"], label_visibility="collapsed")
with tab2:
    camera_photo = st.camera_input("點擊按鈕拍照", key="camera_input", label_visibility="collapsed")

if "image_data" not in st.session_state:
    st.session_state.image_data = None
if camera_photo:
    st.session_state.image_data = Image.open(camera_photo)
elif uploaded_image:
    st.session_state.image_data = Image.open(uploaded_image)
if st.session_state.image_data:
    st.image(st.session_state.image_data, caption