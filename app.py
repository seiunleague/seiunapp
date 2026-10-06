import os
import pandas as pd
import streamlit as st
from supabase import create_client, Client
import paipu_parser

st.set_page_config(page_title="雀魂大会管理", layout="wide")

# ---------------------------------------------------------
# Supabase クライアント初期化処理
# ---------------------------------------------------------
@st.cache_resource
def init_supabase() -> Client:
    # st.secrets または 環境変数から取得
    supabase_url = st.secrets.get("SUPABASE_URL") or os.environ.get("SUPABASE_URL")
    supabase_key = st.secrets.get("SUPABASE_KEY") or os.environ.get("SUPABASE_KEY")

    if not supabase_url or not supabase_key:
        st.error("Supabase の URL または KEY が Secrets に設定されていません。")
        st.stop()

    # 前後の余計な空白や改行コードを除去
    supabase_url = str(supabase_url).strip()
    supabase_key = str(supabase_key).strip()

    return create_client(supabase_url, supabase_key)

try:
    supabase = init_supabase()
except Exception as e:
    st.error(f"Supabase クライアントの初期化に失敗しました: {e}")
    st.stop()


st.title("🀄 雀魂大会管理 - 牌譜スタッツ自動登録")

# 入力フォーム等
paipu_id = st.text_input("牌譜ID (またはURL)", placeholder="261007-xxxxxxxx-xxxx-xxxx")

if st.button("牌譜データを取得・解析"):
    if not paipu_id:
        st.warning("牌譜IDを入力してください。")
    else:
        try:
            # 1. 牌譜データの解析
            with st.spinner("牌譜解析中..."):
                parsed_data = paipu_parser.fetch_and_parse(paipu_id)
            
            st.success("解析完了！")
            st.json(parsed_data)

            # 2. Supabase への保存処理
            with st.spinner("Supabase へ保存中..."):
                records = []
                for seat, stats in parsed_data.items():
                    records.append({
                        "paipu_id": paipu_id,
                        "seat": seat,
                        "horyo_count": stats.get("horyo_count", 0),
                        "hoju_count": stats.get("hoju_count", 0),
                        "riichi_count": stats.get("riichi_count", 0),
                        "furo_count": stats.get("furo_count", 0),
                        "total_agari_pt": stats.get("total_agari_pt", 0),
                        "total_hoju_pt": stats.get("total_hoju_pt", 0),
                    })
                
                # upsert 実行
                # on_conflict="paipu_id, seat" を指定して重複時に上書き更新（UPDATE）させる
                response = supabase.table("scores").upsert(
                    records, 
                    on_conflict="paipu_id, seat"
                ).execute()
                st.success("✅ Supabase へのデータ登録が正常に完了しました！")

        except Exception as e:
            st.error(f"解析・保存処理中にエラーが発生しました: {e}")
            
            # デバッグ情報の表示（原因特定用）
            with st.expander("🔍 デバッグ情報を確認（Secrets読み込み確認）"):
                url_val = st.secrets.get("SUPABASE_URL", "")
                key_val = st.secrets.get("SUPABASE_KEY", "")
                st.write(f"**URL長**: {len(url_val)} 文字")
                st.write(f"**KEY長**: {len(key_val)} 文字")
                st.write(f"**KEYの先頭**: {key_val[:15]}...")
                st.write(f"**KEYの末尾**: ...{key_val[-10:]}")