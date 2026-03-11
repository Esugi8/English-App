import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from gtts import gTTS
import io
import base64

# --- 1. 初期設定 ---
MODEL_NAME = 'gemini-3.1-flash-lite-preview' 

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
# --- TAB 2: 一覧 ---
with tab_list:
    df_l = load_data()
    st.dataframe(df_l[['word', 'meaning', 'status', 'example_en']], use_container_width=True, hide_index=True)

# --- TAB 3: 登録 ---
with tab_add:
    if "editing_item" not in st.session_state: st.session_state.editing_item = None
    c_in, c_m = st.columns([3, 1])
    with c_m: mode = st.radio("入力モード", ["英語から", "日本語から"], key="add_mode")
    with c_in:
        input_text = st.text_input("単語・フレーズを入力:")
        if st.button("AI生成", type="primary"):
            with st.spinner("生成中..."):
                prompt = f"""
                「{input_text}」の情報をJSON形式で返してください。
                {{
                    "word": "{input_text if mode=='英語から' else '英訳'}",
                    "meaning": "意味",
                    "phonetic": "IPA",
                    "example_en": "英文",
                    "example_ja": "和訳",
                    "synonyms": "類語"
                }}
                """
                try:
                    res = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                    st.session_state.editing_item = json.loads(res.text)
                except: st.error("エラーが発生しました。")

    if st.session_state.editing_item:
        ei = st.session_state.editing_item
        col1, col2 = st.columns(2)
        with col1:
            nw = st.text_input("単語", value=to_str(ei.get('word','')))
            nm = st.text_input("意味", value=to_str(ei.get('meaning','')))
            np = st.text_input("発音", value=to_str(ei.get('phonetic','')))
        with col2:
            ns = st.text_input("類語", value=to_str(ei.get('synonyms','')))
            nee = st.text_area("例文(EN)", value=to_str(ei.get('example_en','')))
            nej = st.text_area("例文(JA)", value=to_str(ei.get('example_ja','')))
        b_save, b_can = st.columns([1, 5])
        with b_save:
            if st.button("保存"):
                df_s = load_data()
                nr = pd.DataFrame([{"word": nw, "meaning": nm, "phonetic": np, "example_en": nee, "example_ja": nej, "synonyms": ns, "status": "L"}])
                conn.update(data=pd.concat([df_s, nr], ignore_index=True))
                st.session_state.editing_item = None; st.rerun()
        with b_can:
            if st.button("キャンセル"):
                st.session_state.editing_item = None; st.rerun()

# --- TAB 4: 管理 ---
with tab_manage:
    df_m = load_data()
    if not df_m.empty:
        target = st.selectbox("修正する単語を選択", df_m['word'].tolist(), key="sb_edit")
        row_m = df_m[df_m['word'] == target].iloc[0]; idx_m = df_m[df_m['word'] == target].index[0]
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            m_w = st.text_input("単語", value=to_str(row_m.get('word','')), key="mw")
            m_m = st.text_input("意味", value=to_str(row_m.get('meaning','')), key="mm")
            m_s = st.selectbox("状態", ["L", "M"], index=0 if row_m.get('status')=='L' else 1)
        with c_m2:
            m_ee = st.text_area("例文(EN)", value=to_str(row_m.get('example_en','')), key="mee")
            m_ej = st.text_area("例文(JA)", value=to_str(row_m.get('example_ja','')), key="mej")
        if st.button("更新"):
            df_m.at[idx_m, 'word'] = m_w; df_m.at[idx_m, 'meaning'] = m_m
            df_m.at[idx_m, 'status'] = m_s; df_m.at[idx_m, 'example_en'] = m_ee; df_m.at[idx_m, 'example_ja'] = m_ej
            conn.update(data=df_m); st.success("更新しました"); st.rerun()