import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from gtts import gTTS
import io
import base64

# --- 1. 初期設定 ---
MODEL_NAME = 'gemini-2.5-flash-lite'

try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel(MODEL_NAME)
except Exception as e:
    st.error(f"API設定エラー: {e}")

conn = st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="AI英単語帳", page_icon="🔊", layout="wide")
st.title("📝 AI 英文法・単語帳")

if "editing_item" not in st.session_state:
    st.session_state.editing_item = None

# --- 便利関数 ---

def speak_and_play(text):
    """スマホ対応の音声再生"""
    if not text or pd.isna(text): return
    try:
        tts = gTTS(text=str(text), lang='en', tld='com')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        b64 = base64.b64encode(fp.read()).decode()
        audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
        st.markdown(audio_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"音声生成エラー: {e}")

def load_data():
    return conn.read(ttl=0)

def to_str(val):
    if isinstance(val, list): return ", ".join(map(str, val))
    return str(val) if pd.notna(val) else ""

# --- 2. サイドバー（新規登録） ---
with st.sidebar:
    st.header("1. 新規登録")
    mode = st.radio("入力モード:", ["英語から生成", "日本語から英訳"])
    
    with st.form("generate_form", clear_on_submit=True):
        input_text = st.text_input("テキストを入力:")
        gen_submit = st.form_submit_button("AIで下書きを生成")

    if gen_submit and input_text:
        with st.spinner("AIが構成中..."):
            prompt = f"""
            「{input_text}」について以下のJSON形式のみで返してください。
            {{"word": "{input_text if mode=='英語から生成' else '英訳'}", "meaning": "意味", "phonetic": "発音記号", "example_en": "英文", "example_ja": "和訳", "synonyms": "類語"}}
            """
            try:
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                st.session_state.editing_item = json.loads(response.text)
            except Exception as e:
                st.error(f"エラー: {e}")
    
    st.divider()
    st.subheader("🛠️ データ管理")
    try:
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        if not sheet_url.startswith("http"): sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_url}/edit"
        st.link_button("📊 スプレッドシートを開く", sheet_url)
    except: st.caption("URL未設定")

# --- 3. 新規登録の確認エリア ---
if st.session_state.editing_item:
    st.subheader("2. 生成内容の確認・編集")
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
        
        b1, b2 = st.columns([1, 5])
        with b1:
            if st.button("✅ 保存", type="primary"):
                df = load_data()
                new_row = pd.DataFrame([{"word": new_word, "meaning": new_mean, "phonetic": new_phon, "example_en": new_ex_e, "example_ja": new_ex_j, "synonyms": new_syns}])
                conn.update(data=pd.concat([df, new_row], ignore_index=True))
                st.session_state.editing_item = None
                st.success("保存完了！"); st.rerun()
        with b2:
            if st.button("❌ キャンセル"):
                st.session_state.editing_item = None
                st.rerun()

# --- 4. 既存単語の修正エリア ---
st.divider()
with st.expander("📝 登録済みの単語を修正・AIで再生成"):
    current_df = load_data()
    if not current_df.empty:
        target_word = st.selectbox("単語を選択", current_df['word'].tolist(), key="sel_edit")
        row_data = current_df[current_df['word'] == target_word].iloc[0]

        if "last_target" not in st.session_state or st.session_state.last_target != target_word:
            st.session_state["m_edit"] = to_str(row_data.get('meaning', ''))
            st.session_state["p_edit"] = to_str(row_data.get('phonetic', ''))
            st.session_state["s_edit"] = to_str(row_data.get('synonyms', ''))
            st.session_state["e_edit"] = to_str(row_data.get('example_en', ''))
            st.session_state["j_edit"] = to_str(row_data.get('example_ja', ''))
            st.session_state.last_target = target_word

        if st.button("✨ AIで再生成"):
            with st.spinner("生成中..."):
                prompt = f"英単語「{target_word}」の情報をJSON形式で返してください。"
                res = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                new_info = json.loads(res.text)
                st.session_state["m_edit"] = to_str(new_info.get('meaning')); st.session_state["p_edit"] = to_str(new_info.get('phonetic'))
                st.session_state["s_edit"] = to_str(new_info.get('synonyms')); st.session_state["e_edit"] = to_str(new_info.get('example_en'))
                st.session_state["j_edit"] = to_str(new_info.get('example_ja')); st.rerun()

        st.write("---")
        c_ed1, c_ed2 = st.columns(2)
        with c_ed1:
            st.text_input("意味", key="m_edit"); st.text_input("発音記号", key="p_edit"); st.text_input("類語", key="s_edit")
        with c_ed2:
            st.text_area("例文 (EN)", key="e_edit"); st.text_area("例文 (JA)", key="j_edit")

        if st.button("💾 更新保存"):
            full_df = load_data(); idx = full_df[full_df['word'] == target_word].index[0]
            full_df.at[idx, 'meaning'] = st.session_state["m_edit"]; full_df.at[idx, 'phonetic'] = st.session_state["p_edit"]
            full_df.at[idx, 'synonyms'] = st.session_state["s_edit"]; full_df.at[idx, 'example_en'] = st.session_state["e_edit"]
            full_df.at[idx, 'example_ja'] = st.session_state["j_edit"]
            conn.update(data=full_df); st.success("更新！"); st.rerun()

# --- 5. 一覧表示（復習エリア） ---
st.divider()
st.subheader("📚 登録済みリスト")

# クイズ設定
display_mode = st.radio("クイズ形式:", ["英語メイン (EN → JA)", "日本語メイン (JA → EN)"], horizontal=True)
show_all_answers = st.toggle("すべての詳細を表示", value=False)

df_list = load_data()
if not df_list.empty:
    search = st.text_input("🔍 検索", "")
    for i in range(len(df_list)-1, -1, -1):
        row = df_list.iloc[i]
        word_val = to_str(row.get('word', ''))
        mean_val = to_str(row.get('meaning', ''))
        ex_en = to_str(row.get('example_en', ''))
        
        if not word_val: continue
        if search.lower() not in word_val.lower() and search not in mean_val: continue
            
        # --- カードの作成（各単語の外枠） ---
        with st.container(border=True):
            # 1行目: 単語/意味 と 音声ボタン
            header_col1, header_col2 = st.columns([5, 1])
            with header_col1:
                # 日本語メインモードでも、例文は英語の勉強として常に表示
                if display_mode == "英語メイン (EN → JA)":
                    st.markdown(f"### {word_val}")
                else:
                    st.markdown(f"### {mean_val}")
            with header_col2:
                if st.button("🔊", key=f"play_w_{i}", help="単語の発音"):
                    speak_and_play(word_val)

            # 2行目: 英語例文（エクスパンダーの外にあるので常に表示）
            st.info(f"**Example:** {ex_en}")
            
            # 3行目: エクスパンダー（ここを閉じても例文は見えたまま）
            detail_label = "答え合わせ・詳細を表示"
            with st.expander(detail_label, expanded=show_all_answers):
                c_d1, c_d2 = st.columns([4, 1])
                with c_d1:
                    if display_mode == "英語メイン (EN → JA)":
                        st.write(f"**意味:** {mean_val}")
                    else:
                        st.write(f"**英単語:** {word_val}")
                    
                    st.write(f"**発音記号:** {to_str(row.get('phonetic', '---'))}")
                    if to_str(row.get('synonyms')): st.write(f"**類語:** {row['synonyms']}")
                    st.write(f"**例文訳:** {to_str(row.get('example_ja', ''))}")
                with c_d2:
                    if st.button("🔊例文", key=f"play_ex_{i}", help="例文の読み上げ"):
                        speak_and_play(ex_en)
else:
    st.info("データがありません。")