import streamlit as st
import pandas as pd
import uuid
from supabase import create_client, Client
from fetch_real_paipu import parse_paipu_details, calculate_uma_oka

# ページ基本設定
st.set_page_config(page_title="雀魂大会スコア & スタッツ管理", page_icon="🀄", layout="wide")

SUPABASE_URL = "https://zcdyduueewpwgrxfnlkv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpjZHlkdXVlZXdwd2dyeGZubGt2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTEyMTA4OTcsImV4cCI6MjEwNjc4Njg5N30.ARBADBO0wCdpPqD3DW6lhxdkjA6d5eDNLN6KikbAERg"

@st.cache_resource
def init_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_supabase()

st.title("🀄 雀魂大会 リアルタイムリーダーボード & 詳細スタッツ")

tab1, tab2 = st.tabs(["🏆 総合順位表 & 個人成績", "📝 牌譜登録"])

# --- タブ1: 総合順位表 & 詳細スタッツ ---
with tab1:
    st.subheader("大会総合ランキング")
    if st.button("🔄 最新データに更新"):
        st.rerun()

    response = supabase.table("scores").select("*").execute()
    
    if response.data:
        df_raw = pd.DataFrame(response.data)
        
        # プレイヤーごとの集計
        summary = df_raw.groupby("player_name").agg({
            "total_pt": "sum",
            "raw_score": "mean",
            "rank": "count", # 対局数
            "horyo_count": "sum",
            "hoju_count": "sum",
            "riichi_count": "sum",
            "total_agari_pt": "sum"
        }).reset_index()

        summary.rename(columns={
            "player_name": "選手名",
            "total_pt": "トータル Pt",
            "raw_score": "平均素点",
            "rank": "対局数",
            "horyo_count": "総和了数",
            "hoju_count": "総放銃数",
            "riichi_count": "総立直数",
            "total_agari_pt": "総和了打点"
        }, inplace=True)

        summary["トータル Pt"] = summary["トータル Pt"].round(1)
        summary["平均素点"] = summary["平均素点"].round(0).astype(int)
        
        summary = summary.sort_values(by="トータル Pt", ascending=False).reset_index(drop=True)
        summary.index += 1
        
        st.dataframe(summary, use_container_width=True)
    else:
        st.info("まだ対局データがありません。")

# --- タブ2: 牌譜登録 ---
with tab2:
    st.subheader("対局結果の自動解析登録")
    paipu_url = st.text_input("雀魂の牌譜URLを入力してください", placeholder="https://game.mahjongsoul.com/?paipu=...")
    
    if st.button("牌譜を詳細解析してスコア保存", use_container_width=True):
        if paipu_url:
            with st.spinner("Protobuf アクションログを解読中..."):
                try:
                    parsed_data = parse_paipu_details(paipu_url)
                    p_uuid = parsed_data["uuid"]
                    results = parsed_data["results"]

                    for item in results:
                        record = {
                            "paipu_uuid": p_uuid,
                            "player_name": item["name"],
                            "raw_score": item["raw_score"],
                            "total_pt": item["total_pt"],
                            "rank": item["rank"],
                            "horyo_count": item.get("horyo_count", 0),
                            "hoju_count": item.get("hoju_count", 0),
                            "riichi_count": item.get("riichi_count", 0),
                            "furo_count": item.get("furo_count", 0),
                            "total_agari_pt": item.get("total_agari_pt", 0),
                            "total_hoju_pt": item.get("total_hoju_pt", 0)
                        }
                        supabase.table("scores").insert(record).execute()
                    
                    st.success("詳細スタッツを含む全スコアの登録が完了しました！")
                except Exception as e:
                    st.error(f"解析エラー: {e}")
        else:
            st.warning("URLを入力してください。")