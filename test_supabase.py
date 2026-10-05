import json
from supabase import create_client, Client

# Supabaseの接続情報
SUPABASE_URL = "https://zcdyduueewpwgrxfnlkv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpjZHlkdXVlZXdwd2dyeGZubGt2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTEyMTA4OTcsImV4cCI6MjEwNjc4Njg5N30.ARBADBO0wCdpPqD3DW6lhxdkjA6d5eDNLN6KikbAERg"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def test_insert_data():
    print("--- 1. 選手のエントリーテスト ---")
    player_data = {
        "name": "テスト選手A",
        "jantama_id": "12345678"
    }
    res_player = supabase.table("players").insert(player_data).execute()
    print("選手登録完了:", res_player.data)

    print("\n--- 2. スコア保存テスト ---")
    score_data = {
        "paipu_uuid": "260927-ec5c780b-1772-4941-ae76-eb73eaa0487f_a406440230",
        "player_name": "テスト選手A",
        "raw_score": 45000,
        "total_pt": 65.0,
        "rank": 1
    }
    res_score = supabase.table("scores").insert(score_data).execute()
    print("スコア保存完了:", res_score.data)

def test_fetch_leaderboard():
    print("\n--- 3. リアルタイム順位表データ取得 ---")
    response = supabase.table("scores").select("*").order("total_pt", desc=True).execute()
    print("順位表データ:")
    print(json.dumps(response.data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_insert_data()
    test_fetch_leaderboard()