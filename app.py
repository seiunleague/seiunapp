import streamlit as st
import paipu_parser
from supabase import create_client

# Supabase 初期化

@st.cache_resource
def init_supabase():
    # secrets の階層（[supabase] または直下）のどちらでも対応
    if "supabase" in st.secrets:
        url = st.secrets["supabase"].get("SUPABASE_URL") or st.secrets["supabase"].get("url")
        key = st.secrets["supabase"].get("SUPABASE_KEY") or st.secrets["supabase"].get("key")
    else:
        url = st.secrets.get("SUPABASE_URL") or st.secrets.get("url")
        key = st.secrets.get("SUPABASE_KEY") or st.secrets.get("key")

    if not url or not key:
        st.error("🚨 Supabase の接続情報（URL / KEY）が Streamlit Secrets から取得できませんでした。")
        st.stop()
        
    return create_client(url, key)

supabase = init_supabase()

st.title("🀄 雀魂 牌譜スタッツ自動集計")

paipu_id = st.text_input("牌譜ID (例: 260926-d0190e11-9732-453c-9a83-00e4d48fbb0a)", "")
uploaded_file = st.file_uploader("牌譜バイナリデータ (.pb / .dat) をアップロード", type=["pb", "bin", "dat", "raw"])

if st.button("解析して Supabase に登録"):
    if not paipu_id:
        st.error("牌譜IDを入力してください。")
    elif uploaded_file is None:
        st.error("牌譜バイナリファイルをアップロードしてください。")
    else:
        pb_data = uploaded_file.read()
        st.info(f"📦 読み込み完了: `{len(pb_data)} bytes`")
        
        # バイナリからスタッツ解析
        stats_by_seat = paipu_parser.parse_bytes(pb_data)
        st.write("📊 解析結果:", stats_by_seat)
        
        # Supabase へ Upsert 登録 (on_conflict='paipu_id, seat')
        records = []
        for seat, stat in stats_by_seat.items():
            records.append({
                "paipu_id": paipu_id,
                "seat": seat,
                "horyo_count": stat["horyo_count"],
                "hoju_count": stat["hoju_count"],
                "riichi_count": stat["riichi_count"],
                "furo_count": stat["furo_count"],
                "total_agari_pt": stat["total_agari_pt"],
                "total_hoju_pt": stat["total_hoju_pt"]
            })
            
        try:
            res = supabase.table("scores").upsert(records, on_conflict="paipu_id, seat").execute()
            st.success("🎉 Supabase へのデータ保存・更新が成功しました！")
        except Exception as e:
            st.error(f"🚨 Supabase 保存エラー: {e}")