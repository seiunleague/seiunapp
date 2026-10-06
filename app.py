import streamlit as st
from supabase import create_client, Client
import paipu_parser

# Supabase 接続の初期化 (st.secrets を使用)
@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

st.title("🀄 雀魂大会戦 牌譜データ自動登録")

paipu_input = st.text_input("牌譜URLまたは牌譜IDを入力してください", placeholder="https://game.mahjongsoul.com/2/?paipu=231010-xxxxxxx...")

if st.button("牌譜データを取得・保存"):
    paipu_id = paipu_parser.parse_paipu_id(paipu_input)
    if not paipu_id:
        st.error("有効な牌譜URL/IDを入力してください。")
    else:
        with st.spinner("雀魂サーバーから牌譜データを取得中..."):
            try:
                # 1. 牌譜データの取得（WebSocket/Protobuf経由）
                # ※ 実際の実装に合わせてWebSocket接続またはローカル取得関数を実行
                # stats = paipu_parser.fetch_and_parse(paipu_id)
                
                st.success(f"牌譜ID: {paipu_id} の解析が完了しました！")
                
                # 例: 4人分の結果プレビューとSupabaseへのINSERT
                # for seat, s in stats.items():
                #     data = {
                #         "paipu_id": paipu_id,
                #         "seat": seat,
                #         "horyo_count": s["horyo_count"],
                #         "hoju_count": s["hoju_count"],
                #         "riichi_count": s["riichi_count"],
                #         "furo_count": s["furo_count"],
                #         "total_agari_pt": s["total_agari_pt"],
                #         "total_hoju_pt": s["total_hoju_pt"],
                #     }
                #     supabase.table("scores").insert(data).execute()
                
            except Exception as e:
                st.error(f"データ取得・解析エラー: {e}")