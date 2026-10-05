import json
import re
import requests

def parse_majsoul_paipu(paipu_url_or_code):
    """
    牌譜URLまたはUUIDから、プレイヤー名と最終点数を取得する（概念コード）
    """
    # URLからUUID部分（例: 231003-xxxx-xxxx-xxxx）のみを取り出す
    uuid_match = re.search(r'[0-9]{6}-[0-9a-fA-F\-]{36}', paipu_url_or_code)
    uuid = uuid_match.group(0) if uuid_match else paipu_url_or_code
    
    print(f"解析対象UUID: {uuid}")

    # TODO: 雀魂Webソケット / APIサーバーに接続し、UUIDに対するGameDetailRecordsを取得
    # 実際にはProtocol Buffersでデコードされた結果が返ってきます
    
    # 取得データのイメージ構造
    mock_result = {
        "uuid": uuid,
        "players": [
            {"seat": 0, "name": "選手A (雀魂名)", "raw_score": 42000, "rank": 1},
            {"seat": 1, "name": "選手B (雀魂名)", "raw_score": 28000, "rank": 2},
            {"seat": 2, "name": "選手C (雀魂名)", "raw_score": 18000, "rank": 3},
            {"seat": 3, "name": "選手D (雀魂名)", "raw_score": 12000, "rank": 4},
        ]
    }
    
    return mock_result

if __name__ == "__main__":
    test_code = "https://mahjongsoul.game.yo-star.com/?paipu=231003-12345678-abcd-efgh-ijkl-1234567890ab"
    data = parse_majsoul_paipu(test_code)
    print("\n--- 解析結果 ---")
    print(json.dumps(data, indent=2, ensure_ascii=False))