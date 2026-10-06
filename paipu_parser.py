import re
import requests
import json
from google.protobuf.internal import decoder

def extract_uuid(paipu_input: str) -> str:
    paipu_input = paipu_input.strip()
    match = re.search(r'paipu=([0-9a-zA-Z\-]+)', paipu_input)
    if match:
        uuid_raw = match.group(1)
    else:
        uuid_raw = paipu_input

    return uuid_raw.split('_')[0]


def fetch_and_parse(paipu_input: str) -> dict:
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
        scan_raw_binary(pb_data, stats_by_seat)

    return stats_by_seat


def fetch_paipu_pb(uuid: str) -> bytes:
    urls = [
        f"https://mahjongsoul.game.yo-star.com/danten/paipu/{uuid}",
        f"https://game.mahjongsoul.com/danten/paipu/{uuid}"
    ]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Referer": "https://game.mahjongsoul.com/"
    }
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            if res.status_code == 200 and len(res.content) > 0:
                return res.content
        except Exception as e:
            print(f"Fetch error: {e}")
            
    return None


def scan_raw_binary(data: bytes, stats_by_seat: dict):
    """
    Protobuf バイナリ内の文字列アクション識別子と seat (0-3) の相対位置を全走査
    """
    # 1. 牌譜データ全体のバイト列内で Action/Record 名の位置を検索
    actions = [
        (b"ActionRiichi", "riichi"),
        (b"RecordRiichi", "riichi"),
        (b"ActionChiPengGang", "furo"),
        (b"ActionAnGang", "furo"),
        (b"ActionMingGang", "furo"),
        (b"ActionHule", "hule"),
        (b"RecordHule", "hule"),
    ]

    for pattern, act_type in actions:
        start = 0
        while True:
            idx = data.find(pattern, start)
            if idx == -1:
                break
            
            # 発見位置の後方 50 バイト以内の Varint/数値（seat: 0~3）を探索
            window = data[idx : idx + 60]
            seats = find_seats_in_window(window)
            
            if seats:
                seat = seats[0]
                if act_type == "riichi":
                    stats_by_seat[seat]["riichi_count"] += 1
                elif act_type == "furo":
                    stats_by_seat[seat]["furo_count"] += 1
                elif act_type == "hule":
                    stats_by_seat[seat]["horyo_count"] += 1
                    if len(seats) > 1 and seats[1] != seat:
                        stats_by_seat[seats[1]]["hoju_count"] += 1

            start = idx + len(pattern)


def find_seats_in_window(window: bytes) -> list:
    """
    バイトウィンドウ内から 0~3 範囲の seat 候補値を抽出
    """
    seats = []
    pos = 0
    length = len(window)
    
    while pos < length:
        try:
            key, pos = decoder._DecodeVarint32(window, pos)
            wire_type = key & 0x7
            if wire_type == 0:
                val, pos = decoder._DecodeVarint32(window, pos)
                if 0 <= val <= 3:
                    seats.append(val)
            elif wire_type == 2:
                size, pos = decoder._DecodeVarint32(window, pos)
                pos += size
            elif wire_type == 1:
                pos += 8
            elif wire_type == 5:
                pos += 4
            else:
                pos += 1
        except Exception:
            pos += 1
    return seats