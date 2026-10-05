import streamlit as st
import pandas as pd
from supabase import create_client, Client
from fetch_real_paipu import fetch_majsoul_paipu_direct

# ページ基本設定
st.set_page_config(page_title="雀魂大会スコア管理", page_icon="🀄", layout="centered")

# Supabase接続設定
SUPABASE_URL = "https://zcdyduueewpwgrxfnlkv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpjZHlkdXVlZXdwd2dyeGZubGt2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTEyMTA4OTcsImV4cCI6MjEwNjc4Njg5N30.ARBADBO0wCdpPqD3DW6lhxdkjA6d5eDNLN6KikbAERg"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.title("🀄 雀魂大会 リアルタイムリーダーボード")

# タブ切り替え（順位表 / 牌譜登録）
tab1, tab2 = st.tabs(["🏆 総合順位表", "📝 牌譜URL登録"])

# --- タブ1: 総合順位表 ---
with tab1:
    st.subheader("現在のランキング")
    if st.button("🔄 最新データに更新"):
        st.rerun()

    response = supabase.table("scores").select("player_name, total_pt, raw_score").execute()
    
    if response.data:
        # プレイヤーごとにポイント集計
        leaderboard = {}
        for row in response.data:
            p_name = row["player_name"]
            pt = float(row["total_pt"])
            leaderboard[p_name] = leaderboard.get(p_name, 0.0) + pt

        # データフレーム化して表示
        df = pd.DataFrame(list(leaderboard.items()), columns=["選手名", "トータル Pt"])
        df = df.sort_values(by="トータル Pt", ascending=False).reset_index(drop=True)
        df.index += 1  # 順位を1始まりに
        
        st.dataframe(df, use_container_width=True)
    else:
        st.info("まだ対局データがありません。")

# --- タブ2: 牌譜登録 ---
with tab2:
    st.subheader("対局結果の自動取り込み")
    paipu_url = st.text_input("雀魂の牌譜URLを入力してください", placeholder="https://game.mahjongsoul.com/?paipu=...")
    
    if st.button("牌譜を解析してスコア保存"):
        if paipu_url:
            with st.spinner("牌譜を解析中..."):
                try:
                    parsed_data = fetch_majsoul_paipu_direct(paipu_url)
                    uuid = parsed_data["uuid"]
                    results = parsed_data["results"]

                    for item in results:
                        record = {
                            "paipu_uuid": uuid,
                            "player_name": item["name"],
                            "raw_score": item["raw_score"],
                            "total_pt": item["total_pt"],
                            "rank": item["rank"]
                        }
                        supabase.table("scores").insert(record).execute()
                    
                    st.success("スコアの保存が完了しました！「総合順位表」タブで結果を確認できます。")
                except Exception as e:
                    st.error(f"エラーが発生しました: {e}")
        else:
            st.warning("URLを入力してください。")