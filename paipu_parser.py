import re
import requests
import json
from google.protobuf.internal import decoder

def extract_uuid(paipu_input: str) -> str:
    """
    入力されたURLまたはIDから純粋な牌譜UUID（`_` 以前の文字列）を取り出す
    """
    paipu_input = paipu_input.strip()
    match = re.search(r'paipu=([0-9a-zA-Z\-]+)', paipu_input)
    if match:
        uuid_raw = match.group(1)
    else:
        uuid_raw = paipu_input

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
        parse_paipu_wrapper(pb_data, stats_by_seat)

    return stats_by_seat


def fetch_paipu_pb(uuid: str) -> bytes:
    """
    雀魂のエンドポイントから牌譜バイナリを取得
    """
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


def parse_paipu_wrapper(data: bytes, stats_by_seat: dict):
    """
    Wrapper レイヤーを剥がして内部のアクションログを解析
    """
    pos = 0
    length = len(data)
    
    while pos < length:
        try:
            key, pos = decoder._DecodeVarint32(data, pos)
            field_num = key >> 3
            wire_type = key & 0x7
            
            if wire_type == 2:  # Length-delimited (Inner Payload)
                size, pos = decoder._DecodeVarint32(data, pos)
                sub_bytes = data[pos:pos+size]
                pos += size
                
                # サブバイト列からアクションキーワードと数値パターンを解析
                parse_action_payload(sub_bytes, stats_by_seat)
                # 再帰的解析
                parse_paipu_wrapper(sub_bytes, stats_by_seat)
                
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


def parse_action_payload(payload: bytes, stats_by_seat: dict):
    """
    各アクションブロックから和了・放銃・立直・副露イベントを直接判定
    """
    # 1. 立直 (ActionRiichi / RecordRiichi)
    if b"Riichi" in payload or b"riichi" in payload:
        seat = find_seat_in_payload(payload)
        if seat is not None:
            stats_by_seat[seat]["riichi_count"] += 1

    # 2. 副露 (ActionChiPengGang / ActionAnGang / ActionMingGang)
    elif any(k in payload for k in [b"ChiPeng", b"AnGang", b"MingGang", b"Peng", b"Chi"]):
        seat = find_seat_in_payload(payload)
        if seat is not None:
            stats_by_seat[seat]["furo_count"] += 1

    # 3. 和了・放銃 (ActionHule / RecordHule)
    elif b"Hule" in payload or b"hule" in payload:
        seats = find_all_seats_in_payload(payload)
        if len(seats) >= 1:
            win_seat = seats[0]
            stats_by_seat[win_seat]["horyo_count"] += 1
            
            # 放銃者（ターゲット）の判定
            if len(seats) >= 2:
                target_seat = seats[1]
                if target_seat != win_seat:
                    stats_by_seat[target_seat]["hoju_count"] += 1


def find_seat_in_payload(data: bytes) -> int:
    """
    ペイロード内の最初の Varint フィールド（seat: 0~3）を取り出す
    """
    pos = 0
    length = len(data)
    while pos < length:
        try:
            key, pos = decoder._DecodeVarint32(data, pos)
            wire_type = key & 0x7
            if wire_type == 0:
                val, pos = decoder._DecodeVarint32(data, pos)
                if 0 <= val <= 3:
                    return val
            elif wire_type == 2:
                size, pos = decoder._DecodeVarint32(data, pos)
                pos += size
            elif wire_type == 1:
                pos += 8
            elif wire_type == 5:
                pos += 4
            else:
                break
        except Exception:
            break
    return None


def find_all_seats_in_payload(data: bytes) -> list:
    """
    ペイロード内のすべての Varint フィールド（seat: 0~3）を取り出す
    """
    seats = []
    pos = 0
    length = len(data)
    while pos < length:
        try:
            key, pos = decoder._DecodeVarint32(data, pos)
            wire_type = key & 0x7
            if wire_type == 0:
                val, pos = decoder._DecodeVarint32(data, pos)
                if 0 <= val <= 3:
                    seats.append(val)
            elif wire_type == 2:
                size, pos = decoder._DecodeVarint32(data, pos)
                pos += size
            elif wire_type == 1:
                pos += 8
            elif wire_type == 5:
                pos += 4
            else:
                break
        except Exception:
            break
    return seats