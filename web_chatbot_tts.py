import streamlit as st
import google.generativeai as genai
from gtts import gTTS
import io
import base64

# --- 1. 網頁基礎配置 ---
st.set_page_config(
    page_title="AI 角色對話產生器 (含語音功能)",
    page_icon="🤖",
    layout="centered"
)

# --- (新增) 語音生成與自動播放函數 ---
def text_to_speech_autoplay(text: str, language_tld: str):
    """
    接收文字和語言，生成語音並在 Streamlit 中自動播放。
    """
    try:
        # 使用 gTTS 生成語音
        tts = gTTS(text=text, lang='zh-TW', tld=language_tld, slow=False)
        
        # 將音訊存到記憶體中的 bytes buffer
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        
        # 將音訊轉為 Base64 編碼
        audio_base64 = base64.b64encode(audio_fp.read()).decode('utf-8')
        
        # 建立 HTML audio 標籤來實現自動播放
        # data:audio/mp3;base64,{audio_base64} 是一種 data URI
        audio_html = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
            Your browser does not support the audio element.
        </audio>
        """
        # 使用 st.components.v1.html 來嵌入 HTML
        st.components.v1.html(audio_html, height=0)
    except Exception as e:
        st.error(f"語音生成失敗：{e}")


# --- 2. 設定側邊欄 (Sidebar) ---
st.sidebar.header("⚙️ 設定")

# API Key 設定... (與之前相同)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    api_key = None
if not api_key:
    st.sidebar.warning("偵測不到 API Key！請在 Streamlit Cloud 的 Secrets 中設定 GOOGLE_API_KEY。")
    api_key = st.sidebar.text_input("或者，請在此處臨時輸入您的 Google API Key：", type="password")

# 角色特性設定... (與之前相同)
default_persona = "..." # (您的預設角色描述，此處省略以節省空間)
st.sidebar.subheader("角色特性設定")
persona_prompt = st.sidebar.text_area("請在這裡輸入 AI 的角色描述：", value=default_persona, height=300)

# 模型選擇... (與之前相同)
model_name = st.sidebar.selectbox("選擇模型", ("gemini-1.5-flash-latest", "gemini-1.5-pro-latest"))

# --- (新增) 語音功能設定 ---
st.sidebar.subheader("🔊 語音設定")
# 語音開關
tts_enabled = st.sidebar.toggle("啟用/關閉語音輸出", value=True)

# 語音選擇
voice_options = {
    "台灣 - 標準女聲": "com.tw",
    "美國 - 英語女聲": "us",
    "英國 - 英語女聲": "co.uk",
    "澳洲 - 英語女聲": "com.au",
}
selected_voice_name = st.sidebar.selectbox("選擇語音", list(voice_options.keys()))
selected_voice_tld = voice_options[selected_voice_name]


# --- 3. 主應用程式介面 ---
st.title("🤖 AI 角色對話產生器")
st.caption("👈 請在左側設定您的 API Key、AI 角色與語音功能")


# --- 4. 初始化模型與對話 ---
chat = None
if not api_key:
    st.error("⚠️ 請在左側設定您的 Google API Key 以開始對話。")
elif not persona_prompt.strip():
    st.error("⚠️ 角色的特性設定不能為空！")
else:
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name=model_name, system_instruction=persona_prompt)
        chat = model.start_chat(history=[])
        st.success("模型已成功載入！可以開始對話了。")
    except Exception as e:
        st.error(f"模型或 API Key 載入失敗，請檢查。錯誤訊息：{e}")


# --- 5. 對話歷史記錄管理 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])


# --- 6. 處理使用者輸入與模型互動 ---
if prompt := st.chat_input("您想對 AI 說些什麼？"):
    if chat:
        # 存檔並顯示使用者訊息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 處理 AI 回覆
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("思考中...✍️")
            try:
                response = chat.send_message(prompt)
                full_response = response.text
                message_placeholder.markdown(full_response)

                # --- (新增) 如果語音已啟用，則播放語音 ---
                if tts_enabled:
                    text_to_speech_autoplay(full_response, selected_voice_tld)

            except Exception as e:
                full_response = f"發生錯誤：{e}"
                message_placeholder.error(full_response)
        
        # 存檔 AI 的完整回覆
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    else:
        st.warning("請先完成左側的設定才能開始對話。")