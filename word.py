import streamlit as st
import google.generativeai as genai
import json
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- 1. 初期設定 ---
MODEL_NAME = 'gemini-flash-latest'
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel(MODEL_NAME)
conn = st.connection("gsheets", type=GSheetsConnection)

st.set_page_config(page_title="AI英単語帳 (Flash)", page_icon="📝", layout="wide")
st.title("📝 AI 英文法・単語帳")

# セッション状態の初期化
if "editing_item" not in st.session_state:
    st.session_state.editing_item = None

# --- 2. データ読み込み関数 ---
def load_data():
    return conn.read(ttl=0)

# --- 3. 生成エリア（サイドバー） ---
with st.sidebar:
    st.header("1. 入力設定")
    mode = st.radio("モード選択:", ["英語から生成", "日本語から英訳"])
    
    with st.form("generate_form", clear_on_submit=True):
        input_text = st.text_input("テキストを入力:")
        gen_submit = st.form_submit_button("生成")
        
    st.divider()
    st.subheader("🛠️ データ管理")
    sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    if not sheet_url.startswith("http"):
        sheet_url = f"https://docs.google.com/spreadsheets/d/{sheet_url}/edit"
    
    st.link_button("📊 Googleスプレッドシートを開く", sheet_url)

    if gen_submit and input_text:
        with st.spinner("生成中..."):
            if mode == "英語から生成":
                prompt = f"""英単語「{input_text}」について以下の形式でJSONを返してください。{{"word": "{input_text}", "meaning": "意味", "example_en": "英文", "example_ja": "和訳"}}"""
            else:
                prompt = f"""日本語「{input_text}」の英訳として最適な単語1つと例文をJSONで返してください。{{"word": "英単語", "meaning": "{input_text}", "example_en": "英文", "example_ja": "和訳"}}"""
            
            try:
                response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
                st.session_state.editing_item = json.loads(response.text)
            except Exception as e:
                st.error(f"エラー: {e}")

# --- 4. 編集・確定エリア ---
if st.session_state.editing_item:
    st.subheader("2. 編集して保存")
    with st.container(border=True):
        col1, col2 = st.columns(2)
        with col1:
            ed_word = st.text_input("単語", value=st.session_state.editing_item['word'])
            ed_meaning = st.text_input("意味", value=st.session_state.editing_item['meaning'])
        with col2:
            ed_en = st.text_area("例文 (EN)", value=st.session_state.editing_item['example_en'])
            ed_ja = st.text_area("例文 (JA)", value=st.session_state.editing_item['example_ja'])
        
        if st.button("✅ 保存"):
            df = load_data()
            new_row = pd.DataFrame([{"word": ed_word, "meaning": ed_meaning, "example_en": ed_en, "example_ja": ed_ja}])
            conn.update(data=pd.concat([df, new_row], ignore_index=True))
            st.session_state.editing_item = None
            st.rerun()

# --- 5. 履歴表示エリア（ここを重点的に修正） ---
st.divider()
col_title, col_toggle = st.columns([2, 1])
with col_title:
    st.subheader("📚 単語リスト")
with col_toggle:
    # デフォルトをオフ（False）にする
    show_all_ja = st.toggle("すべての日本語を表示", value=False)

df_display = load_data()

if not df_display.empty:
    search = st.text_input("🔍 検索", "")
    
    for i in range(len(df_display)-1, -1, -1):
        row = df_display.iloc[i]
        if pd.isna(row['word']): continue
        if search.lower() not in row['word'].lower() and search not in str(row['meaning']):
            continue
            
        # タイトルには英語のみを表示（日本語は隠す）
        with st.expander(f"🔤 {row['word']}"):
            # 1. 意味の表示制御
            if show_all_ja:
                st.write(f"**意味:** {row['meaning']}")
            else:
                # 全体表示がオフでも、この項目だけ見たい場合のための「個別に表示」ボタン
                if st.checkbox("意味を表示", key=f"check_m_{i}"):
                    st.write(f"**意味:** {row['meaning']}")
            
            st.info(f"**Example:** {row['example_en']}")
            
            # 2. 例文訳の表示制御
            if show_all_ja:
                st.write(f"**訳:** {row['example_ja']}")
            else:
                if st.checkbox("例文の訳を表示", key=f"check_ex_{i}"):
                    st.write(f"**訳:** {row['example_ja']}")