import requests
from feedgen.feed import FeedGenerator
import datetime

def create_rss():
    # ターゲットはJSONデータ
    json_url = "https://q-portal.riken.jp/data/topics.json"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("量子コンピュータの最新情報を5分おきに自動取得しています")
    fg.language('ja')

    try:
        # ブラウザのふりをしてアクセス
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        res = requests.get(json_url, headers=headers)
        res.raise_for_status()
        
        # JSONをパース（解析）
        articles = res.json()

        for item in articles[:10]: # 最新10件
            fe = fg.add_entry()
            fe.id(str(item['id']))
            fe.title(item['title'])
            # 実際の記事URLはIDを使って組み立てる
            fe.link(href=f"https://q-portal.riken.jp/topics/{item['id']}")
            
            # 日付の処理（JSON内に日付があればそれを使うのがベスト）
            # ここでは便宜上、取得した現在時刻を入れています
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))
            
    except Exception as e:
        print(f"Error: {e}")

    fg.rss_file('feed.xml')

if __name__ == "__main__":
create_rss()

