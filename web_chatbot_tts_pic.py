import streamlit as st
import google.generativeai as genai
from gtts import gTTS
from PIL import Image
import io
import base64

# --- 1. 網頁基礎配置 ---
st.set_page_config(
    page_title="多功能 AI 助理 (文字/語音/圖片)",
    page_icon="✨",
    layout="centered"
)

# --- 語音生成與自動播放函數 ---
def text_to_speech_autoplay(text: str, language_tld: str):
    try:
        tts = gTTS(text=text, lang='zh-TW', tld=language_tld, slow=False)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        audio_base64 = base64.b64encode(audio_fp.read()).decode('utf-8')
        audio_html = f"""
        <audio autoplay>
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mpeg">
        </audio>
        """
        st.components.v1.html(audio_html, height=0)
    except Exception as e:
        st.error(f"語音生成失敗：{e}")

# --- 2. 設定側邊欄 (Sidebar) ---
st.sidebar.header("⚙️ 核心設定")

# API Key 設定
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    api_key = None
if not api_key:
    st.sidebar.warning("尚未設定 API Key！請在 Streamlit Cloud Secrets 中設定。")
    api_key = st.sidebar.text_input("或在此臨時輸入您的 Google API Key：", type="password")

# 角色特性設定
default_persona = "你是一位知識淵博、樂於助人的 AI 助理。"
st.sidebar.subheader("🎭 角色特性設定")
persona_prompt = st.sidebar.text_area("請輸入 AI 的角色描述 (System Prompt)：", value=default_persona, height=200)

# 模型選擇
model_name = st.sidebar.selectbox("選擇模型 (Vision Pro 支援圖片辨識)", ("gemini-1.5-pro-latest", "gemini-1.5-flash-latest"))

# 語音功能設定
st.sidebar.subheader("🔊 語音設定")
tts_enabled = st.sidebar.toggle("啟用/關閉語音輸出", value=True)
voice_options = {"台灣 - 標準女聲": "com.tw", "美國 - 英語女聲": "us", "英國 - 英語女聲": "co.uk"}
selected_voice_name = st.sidebar.selectbox("選擇語音", list(voice_options.keys()))
selected_voice_tld = voice_options[selected_voice_name]

# --- 3. 主應用程式介面 ---
st.title("✨ 多功能 AI 助理")
st.caption("支援文字、語音輸出與圖片辨識功能")

# --- 4. 初始化模型與對話 ---
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
        st.success("模型已成功載入！")
    except Exception as e:
        st.error(f"模型或 API Key 載入失敗：{e}")

# --- 5. 對話歷史記錄管理 ---
if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        # 處理圖片顯示
        if "image" in message:
            st.image(message["image"], width=200)
        st.markdown(message["content"])

# --- (新增) 圖片上傳與管理 ---
uploaded_image = st.file_uploader("上傳圖片進行辨識...", type=["jpg", "jpeg", "png"])
if "image_data" not in st.session_state:
    st.session_state.image_data = None

if uploaded_image:
    st.session_state.image_data = Image.open(uploaded_image)
    st.image(st.session_state.image_data, caption="已上傳圖片", width=200)

# --- 6. 處理使用者輸入與模型互動 ---
if prompt := st.chat_input("請輸入文字或上傳圖片後提問..."):
    if chat:
        # 準備要顯示和存檔的使用者訊息
        user_message_to_display = {"role": "user", "content": prompt}
        if st.session_state.image_data:
             user_message_to_display["image"] = st.session_state.image_data
        
        st.session_state.messages.append(user_message_to_display)
        with st.chat_message("user"):
            if st.session_state.image_data:
                st.image(st.session_state.image_data, width=200)
            st.markdown(prompt)

        # 準備傳送給模型的內容
        model_input = [prompt]
        if st.session_state.image_data:
            model_input.append(st.session_state.image_data)
        
        # 清空已上傳的圖片，避免跟著下一則訊息一起傳送
        st.session_state.image_data = None
        
        # 處理 AI 回覆
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            message_placeholder.markdown("思考中...✍️")
            try:
                response = chat.send_message(model_input)
                full_response = response.text
                message_placeholder.markdown(full_response)
                if tts_enabled:
                    text_to_speech_autoplay(full_response, selected_voice_tld)
            except Exception as e:
                full_response = f"發生錯誤：{e}"
                message_placeholder.error(full_response)
        
        st.session_state.messages.append({"role": "assistant", "content": full_response})
    else:
        st.warning("請先完成左側的設定才能開始對話。")