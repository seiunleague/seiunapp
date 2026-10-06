import json
import re
import urllib.request
import websockets
import asyncio
import liqi_pb2  # 自動生成したProtobufモジュール

def parse_paipu_id(url_or_id: str) -> str:
    """牌譜URLまたは文字列からID(UUID)を抽出"""
    match = re.search(r'paipu=([0-9a-zA-Z\-_]+)', url_or_id)
    if match:
        full_id = match.group(1)
        # _a0 や _a1 などの末尾オプションを除去
        return full_id.split('_')[0]
    return url_or_id.strip()

def extract_game_stats(game_record_bytes: bytes):
    """
    Protobufバイナリから各プレイヤー(席0~3)のスタッツを算出
    """
    game_details = liqi_pb2.GameDetailRecords()
    game_details.ParseFromString(game_record_bytes)

    # 4人分の集計用初期データ
    stats = {
        i: {
            "horyo_count": 0,
            "hoju_count": 0,
            "riichi_count": 0,
            "furo_count": 0,
            "total_agari_pt": 0,
            "total_hoju_pt": 0,
            "final_score": 0
        } for i in range(4)
    }

    # 各アクションレコードの解析
    for record in game_details.records:
        # 和了 (Hule)
        if record.name == ".lq.RecordHule":
            hule = liqi_pb2.RecordHule()
            hule.ParseFromString(record.data)
            for h in hule.hules:
                seat = h.seat
                delta_score = h.delta_scores[seat] if len(h.delta_scores) > seat else 0
                stats[seat]["horyo_count"] += 1
                stats[seat]["total_agari_pt"] += max(0, delta_score)

                # ツモでなく他家からの和了の場合（放銃者の特定）
                if not h.zumo:
                    # 放銃者は delta_scores がマイナスのプレイヤー
                    for idx, ds in enumerate(h.delta_scores):
                        if ds < 0 and idx != seat:
                            stats[idx]["hoju_count"] += 1
                            stats[idx]["total_hoju_pt"] += abs(ds)

        # 立直 (Reach)
        elif record.name == ".lq.RecordReachLiqi":
            reach = liqi_pb2.RecordReachLiqi()
            reach.ParseFromString(record.data)
            if reach.seat in stats:
                stats[reach.seat]["riichi_count"] += 1

        # 副露 (Chi / Peng / Gang)
        elif record.name in [".lq.RecordChiPengGang", ".lq.RecordAnGangAddGang"]:
            # 副露アクションのパース
            action = liqi_pb2.RecordChiPengGang()
            try:
                action.ParseFromString(record.data)
                if action.seat in stats:
                    stats[action.seat]["furo_count"] += 1
            except Exception:
                pass

    return stats

def fetch_and_parse(paipu_id: str) -> dict:
    """
    指定された paipu_id の牌譜データを取得・解析し、各席のスタッツ辞書を返します。
    （WebSocket通信またはフォールバック用のテストデータ生成）
    """
    # 実際の実装がある場合はそれを実行
    # まだ通信実装のテスト段階の場合は、以下のようにダミー/テストデータを返すロジック
    return {
        0: {
            "horyo_count": 2,
            "hoju_count": 1,
            "riichi_count": 3,
            "furo_count": 1,
            "total_agari_pt": 12000,
            "total_hoju_pt": -3000,
        },
        1: {
            "horyo_count": 1,
            "hoju_count": 2,
            "riichi_count": 1,
            "furo_count": 2,
            "total_agari_pt": 3900,
            "total_hoju_pt": -12000,
        },
        2: {
            "horyo_count": 0,
            "hoju_count": 0,
            "riichi_count": 2,
            "furo_count": 0,
            "total_agari_pt": 0,
            "total_hoju_pt": 0,
        },
        3: {
            "horyo_count": 1,
            "hoju_count": 0,
            "riichi_count": 0,
            "furo_count": 3,
            "total_agari_pt": 8000,
            "total_hoju_pt": 0,
        },
    }