import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from gtts import gTTS
import io
import base64

# --- 1. 初期設定 ---
MODEL_NAME = 'gemini-1.5-flash-8b' 

try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    st.error(f"API設定エラー: {e}")

conn = st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="Aligned AI English", page_icon="📝", layout="wide")

# --- 2. カスタムデザイン (CSS) ---
st.markdown("""
<style>
    .stVerticalBlock { gap: 0rem !important; }
    
    /* カード全体のパディング */
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 0.1rem 0.6rem !important;
        margin-bottom: 0.1rem !important;
    }

    /* 単語ハイライト */
    .word-badge {
        background-color: #f1f3f6;
        border-left: 5px solid #1c83e1; 
        padding: 2px 12px;             
        border-radius: 2px;
        font-size: 1.5rem;
        font-weight: bold;
        display: inline-block;
        margin-bottom: 0px;
    }

    /* 例文のスタイル */
    .example-box {
        padding-left: 0px; 
        font-size: 1.2rem;
        line-height: 1.3;
        color: #333;
        margin-top: 20px !important;
        margin-bottom: 15px !important;
    }

    /* 詳細エリア（トグル時）★灰色の線を消去 */
    .detail-area {
        margin-left: 5px;
        font-size: 1.1rem;
        color: #555;
        border-top: none !important; /* 太い線を無効化 */
        padding-top: 5px;
        margin-top: 5px;
        margin-bottom: 10px;
    }

    /* チェックボックスの調整 */
    .stCheckbox { margin-top: 8px !important; }

    /* クリック時の灰色の枠・モヤを無効化 */
    [data-testid="stCheckbox"] *:focus {
        outline: none !important;
        box-shadow: none !important;
    }
    [data-testid="stCheckbox"] div:active {
        background-color: transparent !important;
    }
    [data-testid="stCheckbox"] label span {
        background-color: transparent !important;
    }

    /* ボタンの余白調整 */
    div.stButton > button {
        margin-top: 5px !important;
        padding: 0px 5px !important;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 便利関数 ---
def speak_and_play(text):
    if not text or pd.isna(text): return
    try:
        tts = gTTS(text=str(text), lang='en', tld='com')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        b64 = base64.b64encode(fp.read()).decode()
        audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
        st.markdown(f'<div style="display:none;">{audio_html}</div>', unsafe_allow_html=True)
    except: pass

def load_data():
    df = conn.read(ttl=0)
    if 'status' not in df.columns: df['status'] = 'L'
    return df

def to_str(val):
    if isinstance(val, list): return ", ".join(map(str, val))
    return str(val) if pd.notna(val) else ""

# --- 4. メインレイアウト ---
st.title("📖 AI English Notebook")
tab_study, tab_list, tab_add, tab_manage = st.tabs(["🔥 復習", "📇 一覧", "➕ 登録", "🛠️ 管理"])

# --- TAB 1: 復習 ---
with tab_study:
    df_all = load_data()
    c_s1, c_s2, c_s3 = st.columns([2, 1, 1])
    with c_s1: 
        view_mode = st.radio("形式", ["英語メイン", "日本語メイン"], horizontal=True)
    with c_s2: 
        filter_status = st.checkbox("習得済みも表示", value=False)
    with c_s3: 
        display_count = st.number_input("表示件数", min_value=1, value=20)

    df_review = df_all.copy()
    if not filter_status: df_review = df_review[df_review['status'] != 'M']
    
    search = st.text_input("🔍 検索", key="search_rev")
    if search:
        df_review = df_review[df_review['word'].str.contains(search, case=False, na=False) | 
                              df_review['meaning'].str.contains(search, na=False)]

    df_display = df_review.tail(display_count).iloc[::-1]

    for i, row in df_display.iterrows():
        word_val = to_str(row.get('word', ''))
        mean_val = to_str(row.get('meaning', ''))
        ex_en = to_str(row.get('example_en', ''))
        
        with st.container(border=True):
            cols = st.columns([0.6, 7.5, 0.8, 0.8, 0.8])
            
            with cols[0]:
                show_detail = st.checkbox(" ", key=f"tgl_{i}", label_visibility="collapsed")
            
            with cols[1]:
                display_text = word_val if view_mode == "英語メイン" else mean_val
                st.markdown(f'<div class="word-badge">{display_text}</div>', unsafe_allow_html=True)
                st.markdown(f'<div class="example-box"><b>EX:</b> {ex_en}</div>', unsafe_allow_html=True)
                
                # ★st.divider() を削除しました
                if show_detail:
                    st.markdown(f"""
                    <div class="detail-area">
                        <b>意味:</b> {mean_val if view_mode=='英語メイン' else word_val}<br>
                        <b>発音:</b> {to_str(row.get('phonetic',''))}<br>
                        <b>類語:</b> {to_str(row.get('synonyms',''))}<br>
                        <b>和訳:</b> {to_str(row.get('example_ja',''))}
                    </div>
                    """, unsafe_allow_html=True)

            with cols[2]:
                if st.button("🔊", key=f"sp_{i}"):
                    speak_and_play(word_val)
            
            with cols[3]:
                if st.button("▶️", key=f"spex_{i}"):
                    speak_and_play(ex_en)
            
            with cols[4]:
                if st.button("✅", key=f"ms_{i}"):
                    df_all.at[i, 'status'] = 'M'
                    conn.update(data=df_all); st.rerun()

# (以降のタブは変更なしのため省略。既存のコードをそのままお使いください)