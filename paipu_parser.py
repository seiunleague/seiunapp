import re
import requests

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

    # `_a406440230` などの視点IDが付加されている場合は切り離す
    return uuid_raw.split('_')[0]


def fetch_and_parse(paipu_input: str) -> dict:
    """
    雀魂の牌譜UUIDからログを取得し、各席（0:東家, 1:南家, 2:西家, 3:北家）のスタッツを集計する
    """
    uuid = extract_uuid(paipu_input)
    
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

    # 1. 外部 API または代替取得プロキシ経由でパース済みログを取得
    paipu_json = fetch_paipu_json(uuid)

    if paipu_json:
        parse_json_log(paipu_json, stats_by_seat)

    return stats_by_seat


def fetch_paipu_json(uuid: str) -> dict:
    """
    牌譜プロキシ API から構造化 JSON を取得する
    """
    # 雀魂牌譜変換 API エンドポイント
    url = f"https://amae-koromo.sapk.ch/api/v2/plog/{uuid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.json()
    except Exception as e:
        print(f"API Fetch Error: {e}")
        
    return None


def parse_json_log(data: dict, stats_by_seat: dict):
    """
    取得した JSON ログから各局のイベント（和了・放銃・立直・副露）を正しく集計する
    """
    rounds = data.get("log", [])
    
    for round_data in rounds:
        if not isinstance(round_data, list):
            continue
            
        for action in round_data:
            if not isinstance(action, dict):
                continue
                
            # 1. 立直の検出
            if "riichi" in action or action.get("type") == "riichi":
                seat = action.get("seat")
                if seat is not None and 0 <= int(seat) <= 3:
                    stats_by_seat[int(seat)]["riichi_count"] += 1

            # 2. 副露（チー・ポン・カン）の検出
            elif action.get("type") in ["chi", "peng", "gang", "angang", "minggang"]:
                seat = action.get("seat")
                if seat is not None and 0 <= int(seat) <= 3:
                    stats_by_seat[int(seat)]["furo_count"] += 1

            # 3. 和了・放銃（hule）の検出
            elif action.get("type") == "hule" or "hule" in action:
                hule_info = action.get("hule", action)
                win_seat = hule_info.get("seat")
                target_seat = hule_info.get("target")
                score = hule_info.get("score", 0)

                if win_seat is not None and 0 <= int(win_seat) <= 3:
                    stats_by_seat[int(win_seat)]["horyo_count"] += 1
                    stats_by_seat[int(win_seat)]["total_agari_pt"] += score

                # ロン放銃者の集計（ツモ以外かつ自分以外）
                if target_seat is not None and target_seat != win_seat and 0 <= int(target_seat) <= 3:
                    stats_by_seat[int(target_seat)]["hoju_count"] += 1
                    stats_by_seat[int(target_seat)]["total_hoju_pt"] += score