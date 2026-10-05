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

    # 公開Web APIプロキシ等を経由して牌譜アクションログ(JSON/PB)を取得するフォールバック構造
    # (雀魂Webプロキシエンドポイント例)
    proxy_url = f"https://majsoul-paipu-api.vercel.app/api/paipu/{uuid}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }

    try:
        res = requests.get(proxy_url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            return process_game_actions(uuid, data)
    except Exception:
        pass

    # 取得失敗時のダミー/互換構造（フォールバック）
    raise RuntimeError(f"牌譜 UUID ({uuid}) のアクションログ取得に失敗しました。")


def process_game_actions(uuid: str, game_json: dict) -> dict:
    """
    取得した対局アクションログからスタッツを集計する
    """
    players = game_json.get("players", [])
    actions = game_json.get("actions", []) # 牌譜内アクションリスト

    # プレイヤー初期化
    stats = {
        i: {
            "name": players[i]["nickname"],
            "raw_score": players[i].get("score", 0),
            "horyo_count": 0,
            "hoju_count": 0,
            "riichi_count": 0,
            "furo_count": 0,
            "total_agari_pt": 0,
            "total_hoju_pt": 0,
        }
        for i in range(len(players))
    }

    # アクションログを1局ずつ走査してスタッツ加算
    for act in actions:
        act_type = act.get("type")
        
        # 立直
        if act_type == "riichi":
            seat = act.get("seat")
            stats[seat]["riichi_count"] += 1
            
        # 副露 (ポン/チー/カン)
        elif act_type == "furo":
            seat = act.get("seat")
            stats[seat]["furo_count"] += 1

        # 和了 (ロン / ツモ)
        elif act_type == "hule":
            hules = act.get("hules", [])
            for h in hules:
                seat = h.get("seat")          # 和了者
                delta = h.get("delta_score", 0) # 打点
                stats[seat]["horyo_count"] += 1
                stats[seat]["total_agari_pt"] += delta

                # 放銃者 (ツモ以外)
                target = h.get("target")
                if target is not None and target != seat:
                    stats[target]["hoju_count"] += 1
                    stats[target]["total_hoju_pt"] += delta

    raw_scores = [stats[i]["raw_score"] for i in range(len(players))]
    uma_oka_results = calculate_uma_oka(raw_scores)

    results = []
    for i in range(len(players)):
        item = stats[i]
        item["total_pt"] = uma_oka_results[i]["total_pt"]
        item["rank"] = uma_oka_results[i]["rank"]
        results.append(item)

    return {
        "uuid": uuid,
        "results": results
    }