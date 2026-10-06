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
            "furo_count": 0,      # 副露（ポン・チー・カン）回数
            "total_agari_pt": 0,  # 獲得素点合計
            "total_hoju_pt": 0    # 放銃失点合計
        }
        for seat in range(4)
    }

    # 1. 雀魂サーバーからの牌譜データ（Protobufバイナリ）取得
    pb_data = fetch_paipu_pb(uuid)

    if pb_data:
        # 2. Protobuf/JSON アクションログのパース処理
        parse_paipu_data(pb_data, stats_by_seat)

    return stats_by_seat


def fetch_paipu_pb(uuid: str) -> bytes:
    """
    雀魂の公式エンドポイントから牌譜バイナリを取得する
    """
    url = f"https://mahjongsoul.game.yo-star.com/danten/paipu/{uuid}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://mahjongsoul.game.yo-star.com/"
    }
    
    try:
        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code == 200:
            return res.content
        else:
            print(f"牌譜取得エラー Status Code: {res.status_code}")
            return None
    except Exception as e:
        print(f"通信エラー: {e}")
        return None


def parse_paipu_data(pb_data: bytes, stats_by_seat: dict):
    """
    Protobuf バイナリ / JSON アクション構造の解読処理
    """
    try:
        # 雀魂の牌譜バイナリ内に含まれるテキスト・JSON要素を抽出・フォールバック解析
        # ※ プロトコルバッファ構造内の名 committed action / record data 抽出
        text_content = pb_data.decode('utf-8', errors='ignore')
        
        # 局ごとの和了・放銃・立直・副露イベントをバイナリ/テキストパターンから検出
        # 1. 立直 (ActionRiichi / 立直宣言)
        riichi_matches = re.findall(r'ActionRiichi.*?seat["\':\s]*([0-3])', text_content)
        for seat_str in riichi_matches:
            seat = int(seat_str)
            if seat in stats_by_seat:
                stats_by_seat[seat]["riichi_count"] += 1

        # 2. 副露 (ActionChiPengGang / ポン・チー・カン)
        furo_matches = re.findall(r'ActionChiPengGang.*?seat["\':\s]*([0-3])', text_content)
        for seat_str in furo_matches:
            seat = int(seat_str)
            if seat in stats_by_seat:
                stats_by_seat[seat]["furo_count"] += 1

        # 3. 和了・放銃 (ActionHule)
        # Huleブロック（和了イベント）のパース
        hule_blocks = re.findall(r'ActionHule.*?(?=Action|\Z)', text_content, re.DOTALL)
        for block in hule_blocks:
            # 和了者（hule seat）
            hule_seats = re.findall(r'seat["\':\s]*([0-3])', block)
            # ターゲット（放銃者 target / delta点数）
            target_seats = re.findall(r'delta.*seat["\':\s]*([0-3])', block)
            
            if hule_seats:
                win_seat = int(hule_seats[0])
                if win_seat in stats_by_seat:
                    stats_by_seat[win_seat]["horyo_count"] += 1
                
                # 放銃者の判定（ツモ以外でロン上がりされたプレイヤー）
                for t_str in target_seats:
                    target_seat = int(t_str)
                    if target_seat != win_seat and target_seat in stats_by_seat:
                        stats_by_seat[target_seat]["hoju_count"] += 1

    except Exception as e:
        print(f"パース処理中にエラーが発生しました: {e}")