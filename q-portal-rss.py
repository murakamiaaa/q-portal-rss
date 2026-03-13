import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time

def get_article_body(url):
    """詳細ページから本文を抽出（ここはGETでOK）"""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    try:
        time.sleep(1)
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.find('div', class_='topics-detail-content') or soup.find('article') or soup.find('main')
        return content.get_text(separator="\n", strip=True) if content else "本文なし"
    except:
        return "取得エラー"

def create_rss():
    # 碧さんが見つけたURL
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス (API-POST版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("POSTリクエストでAPIから直接取得しています")

    print(f"--- API(POST)アクセス開始: {datetime.datetime.now()} ---")
    
    # サーバーを納得させるための詳細なヘッダー
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://q-portal.riken.jp",
        "Referer": "https://q-portal.riken.jp/",
        "Content-Type": "application/json", # POSTの時はこれが重要になることが多い
    }

    try:
        # 【重要】requests.get ではなく requests.post を使う
        # データの中身が空でも、POSTという「形式」で送ることが重要です
        res = requests.post(api_url, headers=headers, json={}, timeout=15)
        
        print(f"HTTP Status Code: {res.status_code}")
        res.raise_for_status()
        
        data = res.json()
        articles = data.get('data', []) if isinstance(data, dict) else data

        print(f"成功: {len(articles)} 件の記事を特定しました。")

        for item in articles[:10]:
            title = item.get('title', '無題')
            article_id = item.get('id')
            article_url = f"https://q-portal.riken.jp/topics/{article_id}"
            
            print(f"本文取得中: {title}")
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=article_url)
            fe.description(get_article_body(article_url))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("成功: feed.xml の生成が完了しました！")

    except Exception as e:
        print(f"エラー発生: {e}")
        if 'res' in locals():
            print(f"Response Body (Hint): {res.text[:300]}")

if __name__ == "__main__":
    create_rss()
