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

st.set_page_config(page_title="AI英単語帳 Pro", page_icon="📝", layout="wide")

# --- カスタムCSS（巨大チェックボックス ＆ 余白極小化） ---
st.markdown("""
<style>
    /* 全体の行間を詰める */
    .stVerticalBlock { gap: 0rem !important; }
    
    /* カードコンテナのパディング */
    [data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 0.1rem 0.5rem !important;
        margin-bottom: 0.1rem !important;
    }

    /* 1. チェックボックス（トグル）を巨大化 */
    [data-testid="stCheckbox"] {
        transform: scale(1.8); /* 1.8倍に拡大 */
        transform-origin: left center;
        margin-left: 5px !important;
    }

    /* 2. 単語タイトルのスタイル */
    .word-title {
        font-size: 1.8rem !important;
        font-weight: bold;
        margin: 0 !important;
        margin-left: -1rem !important; /* チェックボックスとの距離 */
        line-height: 1.1;
    }

    /* 3. 例文（青い箱）を単語に極限まで近づける */
    .stAlert {
        padding: 0.1rem 0.5rem !important;
        margin-top: -15px !important; /* マイナス値で上に引き寄せ */
        margin-bottom: 0px !important;
        border: none !important;
        background-color: rgba(28, 131, 225, 0.07) !important;
    }
    .stAlert p {
        font-size: 1.3rem !important;
        line-height: 1.2 !important;
        margin: 0 !important;
    }

    /* ボタンのサイズ */
    div.stButton > button {
        padding: 0px 5px !important;
        height: 2rem !important;
        min-height: 2rem !important;
        font-size: 1.0rem !important;
    }

    /* 詳細テキストのフォントサイズ */
    .detail-text {
        font-size: 1.1rem !important;
        color: #444;
        background: #f0f2f6;
        padding: 8px;
        border-radius: 4px;
        margin-top: 0px;
    }
</style>
""", unsafe_allow_html=True)

# --- 便利関数 ---
def speak_and_play(text):
    if not text or pd.isna(text): return
    try:
        tts = gTTS(text=str(text), lang='en', tld='com')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        b64 = base64.b64encode(fp.read()).decode()
        audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
        st.markdown(audio_html, unsafe_allow_html=True)
    except: pass

def load_data():
    df = conn.read(ttl=0)
    if 'status' not in df.columns: df['status'] = 'L'
    return df

def to_str(val):
    if isinstance(val, list): return ", ".join(map(str, val))
    return str(val) if pd.notna(val) else ""

# --- メインレイアウト ---
st.title("📝 AI 英文法・単語帳 Pro")
tab_review, tab_list, tab_add, tab_manage = st.tabs(["🔥 集中復習", "📇 全単語リスト", "➕ 新規登録", "🛠️ 管理"])

# --- TAB 1: 集中復習 ---
with tab_review:
    df_all = load_data()
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        view_mode = st.radio("形式", ["英語メイン", "日本語メイン"], horizontal=True, key="v_mode")
    with c2:
        filter_status = st.checkbox("習得済みも含む", value=False)
    with c3:
        display_count = st.number_input("件数", min_value=1, max_value=200, value=20)

    df_review = df_all.copy()
    if not filter_status: df_review = df_review[df_review['status'] != 'M']
    
    search_rev = st.text_input("🔍 検索", key="search_rev")
    if search_rev:
        df_review = df_review[df_review['word'].str.contains(search_rev, case=False, na=False) | 
                              df_review['meaning'].str.contains(search_rev, na=False)]

    df_display = df_review.tail(display_count).iloc[::-1]

    for i, row in df_display.iterrows():
        word_val = to_str(row.get('word', ''))
        mean_val = to_str(row.get('meaning', ''))
        ex_en = to_str(row.get('example_en', ''))
        
        with st.container(border=True):
            # カラム比率調整
            c_toggle, c_title, c_sp, c_ms = st.columns([0.6, 8, 0.7, 0.7])
            with c_toggle:
                show_detail = st.checkbox(" ", key=f"tgl_{i}", label_visibility="collapsed")
            with c_title:
                title_text = word_val if view_mode == "英語メイン" else mean_val
                st.markdown(f'<p class="word-title">{"▼ " if show_detail else "▶ "} {title_text}</p>', unsafe_allow_html=True)
            with c_sp:
                if st.button("🔊", key=f"sp_{i}"): speak_and_play(word_val)
            with c_ms:
                if st.button("✅", key=f"ms_{i}"):
                    df_all.at[i, 'status'] = 'M'
                    conn.update(data=df_all)
                    st.rerun()
            
            st.info(f"EX: {ex_en}")
            
            if show_detail:
                st.markdown(f"""
                <div class="detail-text">
                    <b>意味:</b> {mean_val if view_mode=='英語メイン' else word_val}<br>
                    <b>発音:</b> {to_str(row.get('phonetic',''))} / <b>類語:</b> {to_str(row.get('synonyms',''))}<br>
                    <b>和訳:</b> {to_str(row.get('example_ja',''))}
                </div>
                """, unsafe_allow_html=True)
                if st.button("🔊 例文再生", key=f"spex_{i}"): speak_and_play(ex_en)

# --- TAB 2: 全単語リスト ---
with tab_list:
    df_list_view = load_data()
    st.subheader(f"📋 全登録単語（{len(df_list_view)}件）")
    st.dataframe(df_list_view[['word', 'meaning', 'status', 'example_en', 'synonyms']], use_container_width=True, hide_index=True)

# --- TAB 3: 新規登録 ---
with tab_add:
    if "editing_item" not in st.session_state: st.session_state.editing_item = None
    c_in, c_m = st.columns([3, 1])
    with c_m: mode = st.radio("モード", ["英語から生成", "日本語から英訳"], key="add_mode")
    with c_in:
        input_text = st.text_input("登録したい単語・フレーズ:")
        if st.button("AI下書き作成", type="primary"):
            with st.spinner("AI生成中..."):
                if mode == "英語から生成":
                    prompt = f"""「{input_text}」の情報をJSONで。{{"word": "{input_text}", "meaning": "日本語訳(説明不要)", "phonetic": "IPA", "example_en": "英文", "example_ja": "和訳", "synonyms": "類語"}}"""
                else:
                    prompt = f"""日本語「{input_text}」に最適な英単語を選びJSONで。{{"word": "選定単語", "meaning": "{input_text}", "phonetic": "IPA", "example_en": "英文", "example_ja": "和訳", "synonyms": "類語"}}"""
                res = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                st.session_state.editing_item = json.loads(res.text)

    if st.session_state.editing_item:
        ei = st.session_state.editing_item
        col1, col2 = st.columns(2)
        with col1:
            nw, nm, np = st.text_input("単語", value=to_str(ei.get('word',''))), st.text_input("意味", value=to_str(ei.get('meaning',''))), st.text_input("発音", value=to_str(ei.get('phonetic','')))
        with col2:
            ns, nee, nej = st.text_input("類語", value=to_str(ei.get('synonyms',''))), st.text_area("例文(EN)", value=to_str(ei.get('example_en',''))), st.text_area("例文(JA)", value=to_str(ei.get('example_ja','')))
        if st.button("✅ 保存"):
            df = load_data()
            new_row = pd.DataFrame([{"word": nw, "meaning": nm, "phonetic": np, "example_en": nee, "example_ja": nej, "synonyms": ns, "status": "L"}])
            conn.update(data=pd.concat([df, new_row], ignore_index=True))
            st.session_state.editing_item = None; st.rerun()

# --- TAB 4: 管理 ---
with tab_manage:
    df_m = load_data()
    if not df_m.empty:
        target = st.selectbox("修正する単語を選択", df_m['word'].tolist())
        row, idx = df_m[df_m['word'] == target].iloc[0], df_m[df_m['word'] == target].index[0]
        c_m1, c_m2 = st.columns(2)
        with c_m1:
            m_w, m_m, m_p = st.text_input("単", value=to_str(row.get('word',''))), st.text_input("意", value=to_str(row.get('meaning',''))), st.text_input("発", value=to_str(row.get('phonetic','')))
            m_s = st.selectbox("状", ["L", "M"], index=0 if row.get('status')=='L' else 1)
        with c_m2:
            m_sy, m_ee, m_ej = st.text_input("類", value=to_str(row.get('synonyms',''))), st.text_area("例E", value=to_str(row.get('example_en',''))), st.text_area("例J", value=to_str(row.get('example_ja','')))
        if st.button("💾 更新"):
            df_m.at[idx, 'word'], df_m.at[idx, 'meaning'], df_m.at[idx, 'phonetic'] = m_w, m_m, m_p
            df_m.at[idx, 'status'], df_m.at[idx, 'synonyms'], df_m.at[idx, 'example_en'], df_m.at[idx, 'example_ja'] = m_s, m_sy, m_ee, m_ej
            conn.update(data=df_m); st.rerun()
    st.divider()
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    if not str(sheet_url).startswith("http"): sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_url}/edit"
    st.link_button("📊 スプレッドシートを開く", sheet_url)