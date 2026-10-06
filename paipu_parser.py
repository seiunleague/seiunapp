import re
import requests
import json
from google.protobuf.internal import decoder

def extract_uuid(paipu_input: str) -> str:
    """
    入力されたURLまたはIDから純粋な牌譜UUID（`_` 以前の文字列）を取り出す
    例: https://game.mahjongsoul.com/?paipu=260926-xxx_a123 -> 260926-xxx
    """
    paipu_input = paipu_input.strip()
    match = re.search(r'paipu=([0-9a-zA-Z\-]+)', paipu_input)
    if match:
        uuid_raw = match.group(1)
    else:
        uuid_raw = paipu_input

    # `_a406440230` などの視点IDが付録している場合は切り外す
    return uuid_raw.split('_')[0]


def fetch_and_parse(paipu_input: str) -> dict:
    """
    牌譜データを取得し、各席（0:東家, 1:南家, 2:西家, 3:北家）のスタッツを集計する
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

    pb_data = fetch_paipu_pb(uuid)

    if pb_data:
        parse_protobuf_binary(pb_data, stats_by_seat)

    return stats_by_seat


def fetch_paipu_pb(uuid: str) -> bytes:
    """
    雀魂のエンドポイントから牌譜バイナリを取得
    """
    # グローバル版・日本版共通エンドポイントの試行
    urls = [
        f"https://mahjongsoul.game.yo-star.com/danten/paipu/{uuid}",
        f"https://game.mahjongsoul.com/danten/paipu/{uuid}"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://game.mahjongsoul.com/"
    }
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200 and len(res.content) > 0:
                return res.content
        except Exception as e:
            print(f"通信エラー ({url}): {e}")
            
    return None


def extract_strings_from_protobuf(data: bytes) -> list:
    """
    Protobuf バイナリから埋め込まれているテキスト/JSON要素を再帰抽出
    """
    strings = []
    pos = 0
    length = len(data)
    
    while pos < length:
        try:
            key, pos = decoder._DecodeVarint32(data, pos)
            wire_type = key & 0x7
            
            if wire_type == 2:  # Length-delimited
                size, pos = decoder._DecodeVarint32(data, pos)
                sub_data = data[pos:pos+size]
                pos += size
                
                try:
                    text = sub_data.decode('utf-8')
                    # 有効な文字列/JSONらしきものを保持
                    if len(text) > 3:
                        strings.append(text)
                except UnicodeDecodeError:
                    pass
                
                strings.extend(extract_strings_from_protobuf(sub_data))
            elif wire_type == 0:
                _, pos = decoder._DecodeVarint32(data, pos)
            elif wire_type == 1:
                pos += 8
            elif wire_type == 5:
                pos += 4
            else:
                break
        except Exception:
            break
            
    return strings


def parse_protobuf_binary(pb_data: bytes, stats_by_seat: dict):
    """
    抽出された文字列および生バイナリ内のアクションキーワードからスタッツを集計
    """
    extracted_strings = extract_strings_from_protobuf(pb_data)
    full_str = " ".join(extracted_strings)

    # 1. JSON ログ要素の抽出と解析
    parsed_any = False
    for text in extracted_strings:
        if text.startswith('{') and text.endswith('}'):
            try:
                data = json.loads(text)
                name = data.get("name", "")
                data_body = data.get("data", {})
                
                if "Riichi" in name or "riichi" in data_body:
                    seat = data_body.get("seat")
                    if seat is not None and 0 <= int(seat) <= 3:
                        stats_by_seat[int(seat)]["riichi_count"] += 1
                        parsed_any = True

                if any(k in name for k in ["ChiPeng", "AnGang", "MingGang"]):
                    seat = data_body.get("seat")
                    if seat is not None and 0 <= int(seat) <= 3:
                        stats_by_seat[int(seat)]["furo_count"] += 1
                        parsed_any = True

                if "Hule" in name or "hule" in data_body:
                    hule_list = data_body.get("hule", [])
                    if isinstance(hule_list, dict):
                        hule_list = [hule_list]
                        
                    for hule in hule_list:
                        win_seat = hule.get("seat")
                        target_seat = hule.get("target")
                        score = hule.get("score", 0)

                        if win_seat is not None and 0 <= int(win_seat) <= 3:
                            stats_by_seat[int(win_seat)]["horyo_count"] += 1
                            stats_by_seat[int(win_seat)]["total_agari_pt"] += score
                            parsed_any = True

                        if target_seat is not None and target_seat != win_seat and 0 <= int(target_seat) <= 3:
                            stats_by_seat[int(target_seat)]["hoju_count"] += 1
                            stats_by_seat[int(target_seat)]["total_hoju_pt"] += score
                            parsed_any = True
            except Exception:
                pass

    # 2. アクションメッセージの直接スキャン（フォールバック）
    if not parsed_any:
        # Record/Action キーワードパターンのカウント
        for seat in range(4):
            # 席IDに関連付けられたアクション文字列パターンを探査
            riichi_matches = len(re.findall(f'ActionRiichi.*?seat.*?:.*?{seat}', full_str))
            furo_matches = len(re.findall(f'ActionChiPengGang.*?seat.*?:.*?{seat}', full_str))
            
            stats_by_seat[seat]["riichi_count"] += riichi_matches
            stats_by_seat[seat]["furo_count"] += furo_matches