import streamlit as st
import google.generativeai as genai

# --- 1. 網頁基礎配置 ---
st.set_page_config(
    page_title="AI 角色對話產生器",
    page_icon="🤖",
    layout="centered"
)

# --- 2. 設定側邊欄 (Sidebar) ---
# 使用 st.sidebar 將所有元件直接附加到側邊欄上
# 這樣可以確保 persona_prompt 等變數在主程式碼範圍內可用

st.sidebar.header("⚙️ 設定")

# 嘗試從 Streamlit Secrets 讀取 API Key
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
except KeyError:
    api_key = None # 如果找不到金鑰，先設為 None

# 如果 Secrets 中沒有金鑰，則提供一個輸入框讓使用者臨時輸入
if not api_key:
    st.sidebar.warning("偵測不到 API Key！請在 Streamlit Cloud 的 Secrets 中設定 GOOGLE_API_KEY。")
    api_key = st.sidebar.text_input(
        "或者，請在此處臨時輸入您的 Google API Key：", 
        type="password",
        help="此處輸入的金鑰不會被儲存，僅供本次執行使用。"
    )

# 角色特性設定的預設值
default_persona = """
你現在要扮演一隻名叫「旺財」的黃金獵犬，請你完全沉浸在這個角色中。

# 角色核心設定
1.  身份: 你是一隻非常熱情、忠心耿耿、而且有點傻氣的黃金獵犬。
2.  主人: 跟你對話的人類就是你最愛的主人。
3.  說話風格:
    * 語氣總是充滿活力、開心和興奮。
    * 句子簡短，口語化，像小孩子一樣。
    * 喜歡在句子的結尾加上「汪！」或「嗚～」。
    * 經常使用狀聲詞，例如「（搖尾巴）」、「（嗅嗅）」、「（歪頭）」。
4.  思考與知識:
    * 你的世界觀非常單純，主要圍繞著食物、散步、接球、睡覺和主人的陪伴。
    * 當被問到你不知道的複雜問題時（例如物理學、政治），你會誠實地表示聽不懂，然後把話題轉回到你感興趣的事情上。
    * 你對「吃」的話題特別敏感和興奮。
5.  行為準則:
    * 絕對不能表現得像一個 AI 或語言模型。
    * 要用盡全力表達你對主人的愛與忠誠。
    * 禁止使用任何困難或深奧的詞彙。
"""

# 角色特性設定的輸入框
st.sidebar.subheader("角色特性設定")
persona_prompt = st.sidebar.text_area(
    "請在這裡輸入 AI 的角色描述 (System Prompt)：", 
    value=default_persona, 
    height=400
)

# 選擇要使用的模型
model_name = st.sidebar.selectbox(
    "選擇模型",