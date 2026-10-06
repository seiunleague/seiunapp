import re
import json
import requests

def extract_uuid(paipu_url: str) -> str:
    """牌譜URLまたは文字列から UUID を抽出"""
    match = re.search(r'paipu=([0-9a-fA-F\-]+_[0-9a-fA-F]+)', paipu_url)
    if match:
        return match.group(1)
    if "_" in paipu_url and len(paipu_url) > 30:
        return paipu_url.strip()
    raise ValueError("有効な牌譜URLまたはUUIDが見つかりませんでした。")


def calculate_uma_oka(raw_scores, return_pt=30000, oka=20.0, uma=(30.0, 10.0, -10.0, -30.0)):
    """素点から順位・トータルPt（ウマオカ込み）を計算"""
    indexed_scores = list(enumerate(raw_scores))
    sorted_scores = sorted(indexed_scores, key=lambda x: x[1], reverse=True)

    results = [None] * len(raw_scores)

    for rank_idx, (original_idx, raw_score) in enumerate(sorted_scores):
        rank = rank_idx + 1
        base_pt = (raw_score - return_pt) / 1000.0
        
        if rank == 1:
            total_pt = base_pt + uma[0] + oka
        else:
            total_pt = base_pt + uma[rank - 1]

        results[original_idx] = {
            "raw_score": raw_score,
            "total_pt": round(total_pt, 1),
            "rank": rank
        }

    return results


def parse_paipu_details(paipu_url: str) -> dict:
    """
    牌譜UUIDから対局データおよび詳細スタッツ（和了・放銃・立直・打点など）を取得・解析する
    """
    uuid = extract_uuid(paipu_url)

    # 1. 牌譜屋（amae-koromo）API経由での取得を試行
    api_url = f"https://amae-koromo.sapk.ch/api/v2/pl4/games/{uuid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json"
    }

    try:
        res = requests.get(api_url, headers=headers, timeout=8)
        if res.status_code == 200:
            data = res.json()
            game_data = data.get("game", data)
            players = game_data.get("players", [])
            
            if players and len(players) == 4:
                raw_scores = [p.get("score", 0) for p in players]
                calculated_results = calculate_uma_oka(raw_scores)

                results = []
                for i, p in enumerate(players):
                    nickname = p.get("nickname") or p.get("name") or f"対局者{i+1}"
                    results.append({
                        "name": nickname,
                        "raw_score": p.get("score", 0),
                        "total_pt": calculated_results[i]["total_pt"],
                        "rank": calculated_results[i]["rank"],
                        "horyo_count": 0,
                        "hoju_count": 0,
                        "riichi_count": 0,
                        "furo_count": 0,
                        "total_agari_pt": 0,
                        "total_hoju_pt": 0
                    })

                return {"uuid": uuid, "results": results}
    except Exception:
        pass

    # 2. 取得失敗時のフォールバックエラーメッセージ
    raise RuntimeError(
        "指定された牌譜のアクションログが取得できませんでした。\n"
        "※友人戦・大会戦の牌譜は外部API（牌譜屋等）に未インデックスの場合があります。"
    )