import re
import requests
import json
from google.protobuf.internal import decoder

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

    pb_data = fetch_paipu_pb(uuid)

    if pb_data:
        parse_protobuf_binary(pb_data, stats_by_seat)

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


def extract_strings_from_protobuf(data: bytes) -> list:
    """
    Protobuf バイナリから Length-delimited (Wire Type 2) の文字列/バイト列を再帰的に抽出する
    """
    strings = []
    pos = 0
    length = len(data)
    
    while pos < length:
        try:
            key, pos = decoder._DecodeVarint32(data, pos)
            wire_type = key & 0x7
            
            if wire_type == 2:  # Length-delimited (String, Bytes, Embedded Message)
                size, pos = decoder._DecodeVarint32(data, pos)
                sub_data = data[pos:pos+size]
                pos += size
                
                # UTF-8 テキストとしてデコード試行
                try:
                    text = sub_data.decode('utf-8')
                    strings.append(text)
                except UnicodeDecodeError:
                    pass
                
                # ネストされたProtobufメッセージの再帰解析
                strings.extend(extract_strings_from_protobuf(sub_data))
                
            elif wire_type == 0:  # Varint
                _, pos = decoder._DecodeVarint32(data, pos)
            elif wire_type == 1:  # 64-bit
                pos += 8
            elif wire_type == 5:  # 32-bit
                pos += 4
            else:
                break
        except Exception:
            break
            
    return strings


def parse_protobuf_binary(pb_data: bytes, stats_by_seat: dict):
    """
    抽出した Protobuf 文字列・JSONログからスタッツを集計する
    """
    extracted_strings = extract_strings_from_protobuf(pb_data)
    
    for text in extracted_strings:
        # JSON 形式でアクションが含まれている場合の解析
        if text.startswith('{') and text.endswith('}'):
            try:
                data = json.loads(text)
                name = data.get("name", "")
                data_body = data.get("data", {})
                
                # 1. 立直 (RecordRiichi / ActionRiichi)
                if "Riichi" in name or "riichi" in data_body:
                    seat = data_body.get("seat")
                    if seat is not None and 0 <= int(seat) <= 3:
                        stats_by_seat[int(seat)]["riichi_count"] += 1

                # 2. 副露 (RecordChiPengGang / ActionChiPengGang)
                if any(k in name for k in ["ChiPeng", "AnGang", "MingGang"]) or "type" in data_body:
                    seat = data_body.get("seat")
                    if seat is not None and 0 <= int(seat) <= 3:
                        stats_by_seat[int(seat)]["furo_count"] += 1

                # 3. 和了・放銃 (RecordHule / ActionHule)
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

                        # ツモ以外のロン放銃
                        if target_seat is not None and target_seat != win_seat and 0 <= int(target_seat) <= 3:
                            stats_by_seat[int(target_seat)]["hoju_count"] += 1
                            stats_by_seat[int(target_seat)]["total_hoju_pt"] += score

            except Exception:
                pass