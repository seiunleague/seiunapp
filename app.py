import json
import re
import asyncio
import websockets
import liqi_pb2  # 自動生成されたProtobufモジュール

def parse_paipu_id(url_or_id: str) -> str:
    """牌譜URLまたは文字列からID(UUID)を抽出"""
    match = re.search(r'paipu=([0-9a-zA-Z\-_]+)', url_or_id)
    if match:
        full_id = match.group(1)
        return full_id.split('_')[0]
    return url_or_id.strip()

async def async_fetch_paipu(paipu_id: str) -> bytes:
    """
    雀魂のWebSocketサーバーに接続して牌譜レコード(バイナリ)を取得する
    """
    # 雀魂の対局ログ取得用エンドポイント（パブリックノード）
    uri = "wss://game.majoul.com/game-cli" # または wss://hw.majoul.com/
    
    async with websockets.connect(uri) as websocket:
        # FetchGameRecord リクエストメッセージの構築
        req = liqi_pb2.ReqFetchGameRecord()
        req.game_uuid = paipu_id
        
        # 雀魂の通信プロトコル仕様に合わせた包囲メッセージ(FastMessage等)の送受信
        # ※ 取得したバイナリデータを返却
        # （ここではパース対象の detail_records バイナリを返します）
        
        # 簡易実装用の例: 実際のレスポンスから data を取得
        # response_data = await websocket.recv()
        # res = liqi_pb2.ResFetchGameRecord()
        # res.ParseFromString(data)
        # return res.data
        pass

def extract_game_stats(game_details_bytes: bytes):
    """
    Protobufバイナリから各プレイヤー(席0~3)のスタッツを算出
    """
    game_details = liqi_pb2.GameDetailRecords()
    game_details.ParseFromString(game_details_bytes)

    stats = {
        i: {
            "horyo_count": 0,
            "hoju_count": 0,
            "riichi_count": 0,
            "furo_count": 0,
            "total_agari_pt": 0,
            "total_hoju_pt": 0,
        } for i in range(4)
    }

    for record in game_details.records:
        if record.name == ".lq.RecordHule":
            hule = liqi_pb2.RecordHule()
            hule.ParseFromString(record.data)
            for h in hule.hules:
                seat = h.seat
                delta = h.delta_scores[seat] if len(h.delta_scores) > seat else 0
                stats[seat]["horyo_count"] += 1
                stats[seat]["total_agari_pt"] += max(0, delta)

                if not h.zumo:
                    for idx, ds in enumerate(h.delta_scores):
                        if ds < 0 and idx != seat:
                            stats[idx]["hoju_count"] += 1
                            stats[idx]["total_hoju_pt"] += abs(ds)

        elif record.name == ".lq.RecordReachLiqi":
            reach = liqi_pb2.RecordReachLiqi()
            reach.ParseFromString(record.data)
            if reach.seat in stats:
                stats[reach.seat]["riichi_count"] += 1

        elif record.name in [".lq.RecordChiPengGang", ".lq.RecordAnGangAddGang"]:
            action = liqi_pb2.RecordChiPengGang()
            try:
                action.ParseFromString(record.data)
                if action.seat in stats:
                    stats[action.seat]["furo_count"] += 1
            except Exception:
                pass

    return stats

def fetch_and_parse(paipu_id: str):
    """
    app.py から呼び出すメインエントリーポイント関数
    """
    # 1. 非同期でWebSocket通信を行答・牌譜取得
    # game_bytes = asyncio.run(async_fetch_paipu(paipu_id))
    
    # 2. 取得したバイナリからスタッツを抽出
    # return extract_game_stats(game_bytes)
    
    # ※動作テスト用ダミーデータ（WebSocket取得部が未完成の場合の確認用）
    return extract_game_stats_from_id(paipu_id)

def extract_game_stats_from_id(paipu_id: str):
    # テスト用（WebSocket未接続時でもエラーにならず表示を確認するためのダミー）
    return {
        0: {"horyo_count": 2, "hoju_count": 1, "riichi_count": 3, "furo_count": 1, "total_agari_pt": 12000, "total_hoju_pt": 3900},
        1: {"horyo_count": 1, "hoju_count": 2, "riichi_count": 1, "furo_count": 2, "total_agari_pt": 3900, "total_hoju_pt": 8000},
        2: {"horyo_count": 0, "hoju_count": 0, "riichi_count": 2, "furo_count": 0, "total_agari_pt": 0, "total_hoju_pt": 0},
        3: {"horyo_count": 3, "hoju_count": 0, "riichi_count": 1, "furo_count": 1, "total_agari_pt": 18000, "total_hoju_pt": 0},
    }