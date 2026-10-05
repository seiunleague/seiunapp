import json
from supabase import create_client, Client
from fetch_real_paipu import fetch_majsoul_paipu_direct

# Supabase接続設定
SUPABASE_URL = "https://zcdyduueewpwgrxfnlkv.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpjZHlkdXVlZXdwd2dyeGZubGt2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTEyMTA4OTcsImV4cCI6MjEwNjc4Njg5N30.ARBADBO0wCdpPqD3DW6lhxdkjA6d5eDNLN6KikbAERg"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def process_and_save_paipu(paipu_url):
    """
    牌譜URLを受け取り、解析・ポイント計算を行ってSupabaseへ保存する
    """
    print(f"\n--- 牌譜処理を開始します ---")
    # 1. 牌譜の解析とウマオカ計算
    parsed_data = fetch_majsoul_paipu_direct(paipu_url)
    uuid = parsed_data["uuid"]
    results = parsed_data["results"]

    print(f"UUID: {uuid} の対局結果を保存中...")

    # 2. 各対局者のスコアを Supabase の scores テーブルに登録
    for item in results:
        record = {
            "paipu_uuid": uuid,
            "player_name": item["name"],
            "raw_score": item["raw_score"],
            "total_pt": item["total_pt"],
            "rank": item["rank"]
        }
        supabase.table("scores").insert(record).execute()

    print("データベースへの保存が完了しました！")

def show_current_leaderboard():
    """
    現在の累積ポイント順位表を表示する
    """
    print("\n================== リアルタイム総合順位表 ==================")
    response = supabase.table("scores").select("player_name, total_pt, raw_score").execute()
    
    # プレイヤーごとにトータルポイントを集計
    leaderboard = {}
    for row in response.data:
        p_name = row["player_name"]
        pt = float(row["total_pt"])
        leaderboard[p_name] = leaderboard.get(p_name, 0.0) + pt

    # ポイント順（降順）にソートして表示
    sorted_lb = sorted(leaderboard.items(), key=lambda x: x[1], reverse=True)
    for rank, (name, total_pt) in enumerate(sorted_lb, start=1):
        print(f"第 {rank} 位 | {name}: {total_pt:+.1f} pt")
    print("============================================================\n")

if __name__ == "__main__":
    # テスト用牌譜URLの処理
    target_url = "https://game.mahjongsoul.com/?paipu=260927-ec5c780b-1772-4941-ae76-eb73eaa0487f_a406440230"
    
    process_and_save_paipu(target_url)
    show_current_leaderboard()