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
            "furo_count": 0,      # 副露（ポン・チー・カン）回数
            "total_agari_pt": 0,  # 獲得素点合計
            "total_hoju_pt": 0    # 放銃失点合計
        }
        for seat in range(4)
    }

    pb_data = fetch_paipu_pb(uuid)

    if pb_data:
        parse_paipu_binary_direct(pb_data, stats_by_seat)

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


def parse_paipu_binary_direct(pb_data: bytes, stats_by_seat: dict):
    """
    Protobuf バイナリ要素を走査し、アクション名（ActionName）と seat 属性を取得して集計
    """
    # 雀魂のメッセージ名キーワードパターン
    # ActionRiichi / RecordRiichi
    # ActionChiPengGang / ActionAnGang / ActionMingGang
    # ActionHule / RecordHule
    
    pos = 0
    length = len(pb_data)
    
    # 全バイナリからアクション文字列の出現位置と seat をスキャン
    raw_str = str(pb_data)
    
    # 1. 立直の検出
    for seat in range(4):
        # Riichi アクションパターン matches
        riichi_patterns = [
            f"Riichi".encode() + bytes([seat]),
            f"riichi".encode() + bytes([seat]),
            f"ActionRiichi".encode()
        ]
        # パターンカウントの概算
        r_count = raw_str.count(f"ActionRiichi") // 4  # 全体からのフォールバック
        
    # より正確な Protobuf スキャン: 文字列トークンと隣接 varint (seat) の解析
    tokens = extract_protobuf_tokens(pb_data)
    
    for i, token in enumerate(tokens):
        if not isinstance(token, str):
            continue
            
        # 立直イベントの判定
        if "Riichi" in token or "riichi" in token:
            # 付近の数値トークン（seat: 0~3）を探査
            for j in range(max(0, i-3), min(len(tokens), i+4)):
                if isinstance(tokens[j], int) and 0 <= tokens[j] <= 3:
                    stats_by_seat[tokens[j]]["riichi_count"] += 1
                    break

        # 副露イベント（チー・ポン・カン）の判定
        elif any(k in token for k in ["ChiPeng", "AnGang", "MingGang", "Peng", "Chi"]):
            for j in range(max(0, i-3), min(len(tokens), i+4)):
                if isinstance(tokens[j], int) and 0 <= tokens[j] <= 3:
                    stats_by_seat[tokens[j]]["furo_count"] += 1
                    break

        # 和了イベント（Hule）の判定
        elif "Hule" in token or "hule" in token:
            # 付近の seat 情報から和了・放銃を集計
            seats_found = []
            for j in range(max(0, i-5), min(len(tokens), i+10)):
                if isinstance(tokens[j], int) and 0 <= tokens[j] <= 3:
                    seats_found.append(tokens[j])
            
            if seats_found:
                win_seat = seats_found[0]
                stats_by_seat[win_seat]["horyo_count"] += 1
                
                # 放銃者（ターゲット）が存在する場合
                if len(seats_found) > 1:
                    target_seat = seats_found[1]
                    if target_seat != win_seat:
                        stats_by_seat[target_seat]["hoju_count"] += 1


def extract_protobuf_tokens(data: bytes) -> list:
    """
    Protobuf バイナリから varint (数値) と length-delimited (文字列) をトークン配列として抽出
    """
    tokens = []
    pos = 0
    length = len(data)
    
    while pos < length:
        try:
            key, pos = decoder._DecodeVarint32(data, pos)
            wire_type = key & 0x7
            
            if wire_type == 0:  # Varint (数値)
                val, pos = decoder._DecodeVarint32(data, pos)
                tokens.append(val)
            elif wire_type == 2:  # Length-delimited (文字列/バイト列)
                size, pos = decoder._DecodeVarint32(data, pos)
                sub_bytes = data[pos:pos+size]
                pos += size
                
                try:
                    text = sub_bytes.decode('utf-8')
                    tokens.append(text)
                except UnicodeDecodeError:
                    # 再帰的に解析
                    tokens.extend(extract_protobuf_tokens(sub_bytes))
            elif wire_type == 1:
                pos += 8
            elif wire_type == 5:
                pos += 4
            else:
                pos += 1
        except Exception:
            pos += 1
            
    return tokens