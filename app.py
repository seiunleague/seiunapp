import streamlit as st
import pandas as pd
from supabase import create_client, Client
import paipu_parser

@st.cache_resource
def init_supabase() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

st.title("🀄 雀魂牌譜データ自動解析 & 登録")

paipu_input = st.text_input("牌譜URLまたは牌譜IDを入力してください", placeholder="https://game.mahjongsoul.com/2/?paipu=...")

if st.button("牌譜データを取得・解析"):
    paipu_id = paipu_parser.parse_paipu_id(paipu_input)
    if not paipu_id:
        st.error("有効な牌譜URLまたはIDを入力してください。")
    else:
        with st.spinner("雀魂サーバーから牌譜データを解析中..."):
            try:
                # 牌譜解析を実行 (paipu_parser.py 側の実装関数)
                # ※ もしバイナリ直渡し等の場合は実際の関数名・引数に合わせて変更してください
                # game_bytes = fetch_paipu_bytes(paipu_id)
                # stats = paipu_parser.extract_game_stats(game_bytes)
                
                # サンプル確認用データ構造（パース後の辞書データを想定）
                # stats = paipu_parser.get_stats(paipu_id)

                st.success(f"牌譜ID: {paipu_id} の解析が完了しました！")
                
                # --------------------------------------------------
                # 1. 画面上に解析データのプレビューテーブルを表示
                # --------------------------------------------------
                st.subheader("📊 解析結果プレビュー")
                
                rows = []
                for seat, s in stats.items():
                    rows.append({
                        "席": f"席 {seat}",
                        "和了回数": s.get("horyo_count", 0),
                        "放銃回数": s.get("hoju_count", 0),
                        "立直回数": s.get("riichi_count", 0),
                        "副露回数": s.get("furo_count", 0),
                        "和了発生点数": s.get("total_agari_pt", 0),
                        "放銃失点数": s.get("total_hoju_pt", 0),
                    })
                
                df = pd.DataFrame(rows)
                st.dataframe(df, use_container_width=True)

                # --------------------------------------------------
                # 2. Supabase への保存処理
                # --------------------------------------------------
                with st.spinner("Supabase へ保存中..."):
                    for seat, s in stats.items():
                        record_data = {
                            "paipu_id": paipu_id,
                            "seat": seat,
                            "horyo_count": s.get("horyo_count", 0),
                            "hoju_count": s.get("hoju_count", 0),
                            "riichi_count": s.get("riichi_count", 0),
                            "furo_count": s.get("furo_count", 0),
                            "total_agari_pt": s.get("total_agari_pt", 0),
                            "total_hoju_pt": s.get("total_hoju_pt", 0),
                        }
                        supabase.table("scores").upsert(record_data).execute()
                    
                    st.success("✅ Supabase への保存が完了しました！")

            except Exception as e:
                st.error(f"データ解析・保存エラー: {e}")