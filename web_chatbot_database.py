import sys
import streamlit as st
import google.generativeai as genai

# --- 環境診斷 ---
st.title("🔍 雲端環境診斷資訊")
st.header("Python 直譯器路徑:")
st.code(sys.executable)
st.header("google-generativeai 套件版本:")
st.code(genai.__version__)
st.info("請將以上資訊截圖或複製給 AI 助理進行分析。")
