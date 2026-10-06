import re
import requests
import streamlit as st

def extract_uuid(paipu_input: str) -> str:
    """
    入力文字列から牌譜 UUID（`260926-xxxx-xxxx...`）を抽出する
    """
    paipu_input = paipu_input.strip()
    match = re.search(r'paipu=([0-9a-zA-Z\-]+)', paipu_input)
    if match:
        uuid_raw = match.group(1)
    else:
        uuid_raw = paipu_input

    return uuid_raw.split('_')[0]


def fetch_and_parse(paipu_input: str) -> dict:
    uuid = extract_uuid(paipu_input)
    st.info(f"🔍 解析対象 UUID: `{uuid}`")
    
    stats_by_seat = {
        seat: {
            "horyo_count": 0,     # 和了回数
            "hoju_count": 0,      # 放銃回数
            "riichi_count": 0,    # 立直回数
            "furo_count": 0,      # 副露回数
            "total_agari_pt": 0,  # 獲得素点合計
            "total_hoju_pt": 0    # 放銃失点合計
        }
        for seat in range(4)
    }

    paipu_json = fetch_paipu_json(uuid)

    if paipu_json:
        parse_json_log(paipu_json, stats_by_seat)
        st.success("✅ 牌譜データの解析に成功しました！")
    else:
        st.error("❌ 牌譜データの取得に失敗しました。UUID または API 接続を確認してください。")

    return stats_by_seat


def fetch_paipu_json(uuid: str) -> dict:
    """
    牌譜プロキシ API から JSON を取得
    """
    url = f"https://amae-koromo.sapk.ch/api/v2/plog/{uuid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        st.caption(f"🌐 API レスポンスステータス: `{res.status_code}`")
        
        if res.status_code == 200:
            return res.json()
        else:
            st.warning(f"⚠️ API エラーレスポンス (HTTP {res.status_code}): {res.text[:200]}")
    except Exception as e:
        st.error(f"🚨 通信例外が発生しました: {e}")
        
    return None


def parse_json_log(data: dict, stats_by_seat: dict):
    """
    JSON ログからイベントを集計
    """
    rounds = data.get("log", [])
    if not rounds and "rounds" in data:
        rounds = data.get("rounds", [])
        
    st.caption(f"📊 総局数: {len(rounds)} 局")

    for round_data in rounds:
        if not isinstance(round_data, list):
            continue
            
        for action in round_data:
            if not isinstance(action, dict):
                continue
                
            # 立直
            if "riichi" in action or action.get("type") == "riichi":
                seat = action.get("seat")
                if seat is not None and 0 <= int(seat) <= 3:
                    stats_by_seat[int(seat)]["riichi_count"] += 1

            # 副露
            elif action.get("type") in ["chi", "peng", "gang", "angang", "minggang"]:
                seat = action.get("seat")
                if seat is not None and 0 <= int(seat) <= 3:
                    stats_by_seat[int(seat)]["furo_count"] += 1

            # 和了・放銃
            elif action.get("type") == "hule" or "hule" in action:
                hule_info = action.get("hule", action)
                win_seat = hule_info.get("seat")
                target_seat = hule_info.get("target")
                score = hule_info.get("score", 0)

                if win_seat is not None and 0 <= int(win_seat) <= 3:
                    stats_by_seat[int(win_seat)]["horyo_count"] += 1
                    stats_by_seat[int(win_seat)]["total_agari_pt"] += score

                if target_seat is not None and target_seat != win_seat and 0 <= int(target_seat) <= 3:
                    stats_by_seat[int(target_seat)]["hoju_count"] += 1
                    stats_by_seat[int(target_seat)]["total_hoju_pt"] += score