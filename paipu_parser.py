import re
import requests
import streamlit as st
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
    st.info(f"🔍 解析対象 UUID: `{uuid}`")
    
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

    # 1. 雀魂公式サーバーから牌譜バイナリを直接取得
    pb_data = fetch_paipu_pb(uuid)

    if pb_data:
        st.caption(f"📦 牌譜バイナリ取得成功: `{len(pb_data)} bytes`")
        parse_binary_actions(pb_data, stats_by_seat)
        st.success("✅ 牌譜バイナリの解析が完了しました！")
    else:
        st.error("❌ 牌譜データの取得に失敗しました。UUID を確認してください。")

    return stats_by_seat


def fetch_paipu_pb(uuid: str) -> bytes:
    urls = [
        f"https://mahjongsoul.game.yo-star.com/danten/paipu/{uuid}",
        f"https://game.mahjongsoul.com/danten/paipu/{uuid}"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://game.mahjongsoul.com/"
    }
    
    for url in urls:
        try:
            res = requests.get(url, headers=headers, timeout=10)
            st.caption(f"🌐 Fetch `{url}` -> HTTP `{res.status_code}` (`{len(res.content)}` bytes)")
            if res.status_code == 200 and len(res.content) > 0:
                return res.content
        except Exception as e:
            st.warning(f"⚠️️ Fetch Error (`{url}`): {e}")
            
    return None


def parse_binary_actions(data: bytes, stats_by_seat: dict):
    """
    Protobuf バイナリから Action/Record タグをスキャンし、各席の数値を集計
    """
    # 雀魂のアクション文字列パターン
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
            # パターン発見位置の後方 80 バイトから seat (0~3) を探査
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
    """
    バイトウィンドウ内から seat 候補（0~3）を解析
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