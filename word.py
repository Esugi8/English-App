import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from gtts import gTTS
import io
import base64

# --- 1. 初期設定 ---
MODEL_NAME = 'gemini-2.0-flash'

# API・接続設定
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    st.error(f"Gemini API設定エラー: {e}")

conn = st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="AI英単語帳 (Mobile Audio Fix)", page_icon="🔊", layout="wide")
st.title("📝 AI 英文法・単語帳")

# セッション状態の初期化
if "editing_item" not in st.session_state:
    st.session_state.editing_item = None

# --- 便利関数 ---

def speak_and_play(text):
    """音声をBase64形式で生成し、HTML5オーディオタグで即時再生する（スマホ対策）"""
    if not text or pd.isna(text):
        return
    try:
        tts = gTTS(text=str(text), lang='en', tld='com')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        
        # 音声データをBase64に変換
        b64 = base64.b64encode(fp.read()).decode()
        # HTML5オーディオタグを埋め込んで自動再生
        # ※スマホブラウザの「ユーザー操作による再生」として認識させるため
        audio_html = f"""
            <audio autoplay="true">
                <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(audio_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"音声生成エラー: {e}")

def load_data():
    """スプレッドシートから最新データを読み込み"""
    return conn.read(ttl=20)

def to_str(val):
    """AIの返り値を安全に文字列に変換"""
    if isinstance(val, list):
        return ", ".join(map(str, val))
    return str(val) if pd.notna(val) else ""

# --- 2. サイドバー（新規登録） ---
with st.sidebar:
    st.header("1. 新規登録")
    mode = st.radio("入力モード:", ["英語から生成", "日本語から英訳"])
    
    with st.form("generate_form", clear_on_submit=True):
        input_text = st.text_input("テキストを入力:")
        gen_submit = st.form_submit_button("AIで下書きを生成")

    if gen_submit and input_text:
        with st.spinner("AIが最適な表現を構成中..."):
            if mode == "英語から生成":
                prompt = f"""英単語「{input_text}」について以下の情報をJSON形式で返してください。{{"word": "{input_text}", "meaning": "意味", "phonetic": "発音記号(IPA)", "example_en": "英文", "example_ja": "和訳", "synonyms": "類語(3つ)"}}"""
            else:
                prompt = f"""日本語「{input_text}」に最適な英単語を1つ選びJSONで返してください。{{"word": "選定した英単語", "meaning": "{input_text}", "phonetic": "発音記号(IPA)", "example_en": "英文", "example_ja": "和訳", "synonyms": "類語(3つ)"}}"""
            try:
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                st.session_state.editing_item = json.loads(response.text)
            except Exception as e:
                st.error(f"生成エラー: {e}")
    
    st.divider()
    st.subheader("🛠️ データ管理")
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        if not sheet_url.startswith("http"):
            sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_url}/edit"
        st.link_button("📊 スプレッドシートを開く", sheet_url)
    except:
        st.caption("URL設定なし")

# --- 3. 新規登録の確認エリア ---
if st.session_state.editing_item:
    st.subheader("2. 内容の確認・保存 (新規)")
    with st.container(border=True):
        ei = st.session_state.editing_item
        c1, c2, c3 = st.columns(3)
        with c1:
            new_word = st.text_input("単語", value=to_str(ei.get('word','')), key="new_w")
            new_phon = st.text_input("発音記号", value=to_str(ei.get('phonetic','')), key="new_p")
        with c2:
            new_mean = st.text_input("意味", value=to_str(ei.get('meaning','')), key="new_m")
            new_syns = st.text_input("類語", value=to_str(ei.get('synonyms','')), key="new_s")
        with c3:
            new_ex_e = st.text_area("例文 (EN)", value=to_str(ei.get('example_en','')), key="new_ee")
            new_ex_j = st.text_area("例文 (JA)", value=to_str(ei.get('example_ja','')), key="new_ej")
        
        if st.button("✅ 保存", type="primary"):
            df = load_data()
            new_row = pd.DataFrame([{"word": new_word, "meaning": new_mean, "phonetic": new_phon, "example_en": new_ex_e, "example_ja": new_ex_j, "synonyms": new_syns}])
            conn.update(data=pd.concat([df, new_row], ignore_index=True))
            st.session_state.editing_item = None
            st.success("保存しました！")
            st.rerun()

# --- 4. 既存単語の修正・AI再生成エリア ---
st.divider()
with st.expander("📝 登録済みの単語を修正・AIで情報を補完する"):
    current_df = load_data()
    if not current_df.empty:
        target_word = st.selectbox("修正したい単語を選択", current_df['word'].tolist(), key="select_edit_target")
        row_data = current_df[current_df['word'] == target_word].iloc[0]

        if "last_target" not in st.session_state or st.session_state.last_target != target_word:
            st.session_state["m_edit"] = to_str(row_data.get('meaning', ''))
            st.session_state["p_edit"] = to_str(row_data.get('phonetic', ''))
            st.session_state["s_edit"] = to_str(row_data.get('synonyms', ''))
            st.session_state["e_edit"] = to_str(row_data.get('example_en', ''))
            st.session_state["j_edit"] = to_str(row_data.get('example_ja', ''))
            st.session_state.last_target = target_word

        if st.button("✨ この単語の情報をAIで再生成"):
            with st.spinner("AIが再生成中..."):
                prompt = f"""英単語「{target_word}」の情報をJSON形式で返してください。{{"meaning": "意味", "phonetic": "発音記号", "example_en": "例文", "example_ja": "和訳", "synonyms": "類語"}}"""
                try:
                    res = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                    new_info = json.loads(res.text)
                    st.session_state["m_edit"] = to_str(new_info.get('meaning'))
                    st.session_state["p_edit"] = to_str(new_info.get('phonetic'))
                    st.session_state["s_edit"] = to_str(new_info.get('synonyms'))
                    st.session_state["e_edit"] = to_str(new_info.get('example_en'))
                    st.session_state["j_edit"] = to_str(new_info.get('example_ja'))
                    st.rerun()
                except Exception as e: st.error(f"失敗: {e}")

        st.write("---")
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("意味", key="m_edit")
            st.text_input("発音記号", key="p_edit")
            st.text_input("類語", key="s_edit")
        with col2:
            st.text_area("例文 (EN)", key="e_edit")
            st.text_area("例文 (JA)", key="j_edit")

        if st.button("💾 更新保存"):
            full_df = load_data()
            idx = full_df[full_df['word'] == target_word].index[0]
            full_df.at[idx, 'meaning'] = st.session_state["m_edit"]
            full_df.at[idx, 'phonetic'] = st.session_state["p_edit"]
            full_df.at[idx, 'synonyms'] = st.session_state["s_edit"]
            full_df.at[idx, 'example_en'] = st.session_state["e_edit"]
            full_df.at[idx, 'example_ja'] = st.session_state["j_edit"]
            conn.update(data=full_df)
            st.success("更新完了！")
            st.rerun()

# --- 5. 一覧表示（復習エリア） ---
st.divider()
c_title, c_toggle = st.columns([2, 1])
with c_title:
    st.subheader("📚 登録済みリスト")
with c_toggle:
    show_all = st.toggle("すべての詳細を表示", value=False)

df_list = load_data()
if not df_list.empty:
    search = st.text_input("🔍 検索", "")
    for i in range(len(df_list)-1, -1, -1):
        row = df_list.iloc[i]
        if pd.isna(row.get('word')): continue
        if search.lower() not in str(row['word']).lower() and search not in str(row.get('meaning','')): continue
            
        with st.expander(f"🔤 {row['word']}"):
            col_ph, col_au = st.columns([3, 1])
            with col_ph: st.write(f"**発音記号:** {to_str(row.get('phonetic', '---'))}")
            with col_au:
                if st.button("🔊 再生", key=f"au_w_{i}"):
                    speak_and_play(row['word'])

            if show_all or st.checkbox("意味・類語を表示", key=f"chk_m_{i}"):
                st.write(f"**意味:** {row.get('meaning','')}")
                if to_str(row.get('synonyms')): st.write(f"**類語:** {row['synonyms']}")
            
            st.info(f"**Example:** {to_str(row.get('example_en', ''))}")
            if st.button("🔊 例文再生", key=f"au_ex_{i}"):
                speak_and_play(row.get('example_en', ''))

            if show_all or st.checkbox("例文の訳を表示", key=f"chk_ex_{i}"):
                st.write(f"**訳:** {to_str(row.get('example_ja', ''))}")