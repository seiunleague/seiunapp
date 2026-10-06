import re
import requests
import json

def extract_uuid(paipu_input: str) -> str:
    """
    入力された文字列（URLまたは牌譜ID単体）から 261007-xxxx-xxxx... のUUID形式を取り出す
    """
    paipu_input = paipu_input.strip()
    
    # URL形式（例: https://mahjongsoul.game.yo-star.com/?paipu=261007-xxxxx）からの抽出
    match = re.search(r'paipu=([0-9a-zA-Z\-]+)', paipu_input)
    if match:
        return match.group(1)
    
    # ID単体指定の場合
    return paipu_input


def fetch_and_parse(paipu_input: str) -> dict:
    """
    牌譜ID/URLを受け取り、各席（0:東家, 1:南家, 2:西家, 3:北家）のスタッツを集計して返す
    """
    uuid = extract_uuid(paipu_input)
    
    # TODO: 雀魂API/Protoデータからの直接取得・復号ロジック
    # 現状は構造確認および動作検証のための実用フォーマットを返します
    
    # 初期スタッツ構造（0~3家）
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

    # API取得ロジック（拡張用スケルトン）
    # 例: requests.get(...) などの外部プロキシや自作エンドポイント経由でのログ取得
    
    return stats_by_seat