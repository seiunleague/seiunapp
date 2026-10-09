import streamlit as st
from google.protobuf.internal import decoder

def parse_bytes(pb_data: bytes) -> dict:
    """
    受け取った牌譜バイナリ（bytes）から各席（0:東家, 1:南家, 2:西家, 3:北家）のスタッツを集計する
    """
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

    parse_binary_actions(pb_data, stats_by_seat)
    return stats_by_seat


def parse_binary_actions(data: bytes, stats_by_seat: dict):
    """
    Protobuf バイナリ内の Action/Record タグをスキャンして集計
    """
    patterns = [
        (b"ActionRiichi", "riichi"),
        (b"RecordRiichi", "riichi"),
        (b"ActionChiPengGang", "furo"),
        (b"ActionAnGang", "furo"),
        (b"ActionMingGang", "furo"),
        (b"ActionHule", "hule"),
        (b"RecordHule", "hule"),
    ]

    total_matches = 0
    for pattern, act_type in patterns:
        start = 0
        while True:
            idx = data.find(pattern, start)
            if idx == -1:
                break
            
            total_matches += 1
            window = data[idx : idx + 80]
            seats = extract_varint_seats(window)
            
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

    st.caption(f"🎯 検出アクションパターン数: `{total_matches}` 件")


def extract_varint_seats(window: bytes) -> list:
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