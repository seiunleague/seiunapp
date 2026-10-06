import streamlit as st
import pandas as pd
from supabase import create_client, Client
import paipu_parser

# ページ基本設定
st.set_page_config(
    page_title="雀魂大会戦 牌譜自動登録",
    page_icon="🀄",
    layout="wide"
)

# Supabase 接続の初期化 (st.secrets の安全な読み込み)
@st.cache_resource
def init_supabase() -> Client:
    try:
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
        if not url or not key:
            st.error("⚠️ Streamlit Secrets に SUPABASE_URL または SUPABASE_KEY が設定されていません。アプリ設定の Secrets を確認してください。")
            st.stop()
        return create_client(url, key)
    except Exception as e:
        st.error(f"⚠️ Supabase 接続エラー: {e}")
        st.stop()

supabase = init_supabase()

st.title("🀄 雀魂大会戦 牌譜データ自動登録")
st.write("牌譜URLを入力して解析し、スタッツをSupabaseデータベースに登録・保存します。")

# 入力フォームエリア
with st.form("paipu_form"):
    paipu_url = st.text_input(
        "牌譜URLまたはID",
        placeholder="https://game.mahjongsoul.com/?paipu=261006-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    )
    submitted = st.form_submit_button("牌譜データを取得・解析")

if submitted:
    if not paipu_url.strip():
        st.warning("⚠️ 牌譜URLまたはIDを入力してください。")
    else:
        # URLからIDの抽出
        paipu_id = paipu_parser.parse_paipu_id(paipu_url)
        st.info(f"解析対象 牌譜ID: `{paipu_id}`")
        
        with st.spinner("雀魂サーバーから牌譜データを取得・解析中..."):
            try:
                # 牌譜データの取得＆解析
                stats_dict = paipu_parser.fetch_and_parse(paipu_id)
                
                # 表示用・保存用データフレームの構築
                data_list = []
                for seat, stat in stats_dict.items():
                    data_list.append({
                        "paipu_id": paipu_id,
                        "seat": seat,
                        "horyo_count": stat.get("horyo_count", 0),
                        "hoju_count": stat.get("hoju_count", 0),
                        "riichi_count": stat.get("riichi_count", 0),
                        "furo_count": stat.get("furo_count", 0),
                        "total_agari_pt": stat.get("total_agari_pt", 0),
                        "total_hoju_pt": stat.get("total_hoju_pt", 0),
                    })
                
                df = pd.DataFrame(data_list)
                
                st.subheader("📊 解析結果プレビュー")
                st.dataframe(df, width=1200)
                
                # Supabase `scores` テーブルへの書き込み / 更新 (Upsert)
                with st.spinner("Supabase データベースにデータ書き込み中..."):
                    res = supabase.table("scores").upsert(data_list).execute()
                    
                st.success("✅ Supabase へのデータ登録が正常に完了しました！")
                
            except Exception as e:
                st.error(f"❌ 解析・保存処理中にエラーが発生しました: {e}")

# 登録済みデータの閲覧セクション
st.markdown("---")
st.subheader("📋 登録済み対局データ一覧 (最新10件)")

if st.button("最新データを読み込む"):
    try:
        response = supabase.table("scores").select("*").order("created_at", desc=True).limit(10).execute()
        if response.data:
            registered_df = pd.DataFrame(response.data)
            st.dataframe(registered_df, width=1200)
        else:
            st.info("登録済みのデータはまだありません。")
    except Exception as e:
        st.error(f"⚠️ データ取得エラー: {e}")