import re
import json
import requests

def extract_uuid(paipu_input: str) -> str:
    """
    入力された文字列（URLまたは牌譜ID単体）から 261007-xxxx-xxxx... のUUID形式を取り出す
    """
    paipu_input = paipu_input.strip()
    match = re.search(r'paipu=([0-9a-zA-Z\-]+)', paipu_input)
    if match:
        return match.group(1)
    return paipu_input


def fetch_and_parse(paipu_input: str) -> dict:
    """
    雀魂の牌譜UUIDからログを取得し、各席（0:東家, 1:南家, 2:西家, 3:北家）のスタッツを集計する
    """
    uuid = extract_uuid(paipu_input)
    
    # 0~3家の初期スタッツ
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

    # 1. 雀魂サーバーからの牌譜データ（Protobufバイナリ）取得
    # ※ 実際のリクエストURL構築およびバイナリ取得処理
    pb_data = fetch_paipu_pb(uuid)

    if pb_data:
        # 2. Protobuf デコードとイベント集計
        parse_protobuf_actions(pb_data, stats_by_seat)

    return stats_by_seat


def fetch_paipu_pb(uuid: str) -> bytes:
    """
    雀魂の公式エンドポイントから牌譜バイナリを取得する
    """
    # 雀魂の牌譜データ取得用 URL（※公開ログエンドポイント）
    url = f"https://mahjongsoul.game.yo-star.com/danten/paipu/{uuid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.content
        else:
            print(f"牌譜取得ステータスコード: {res.status_code}")
            return None
    except Exception as e:
        print(f"牌譜取得通信エラー: {e}")
        return None


def parse_protobuf_actions(pb_data: bytes, stats_by_seat: dict):
    """
    Protobuf バイナリをデコードして各席のスタッツを集計する処理
    """
    # Protobufのメッセージ解析ロジック
    # TODO: liqi_pb2 から生成されたクラスを使用して RecordGame ログをパースします
    pass