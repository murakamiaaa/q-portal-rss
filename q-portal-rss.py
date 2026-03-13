import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time

def get_article_body(url):
    """詳細ページから本文を抽出する"""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    try:
        time.sleep(1) # 礼儀
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Q-Portalの本文が含まれるタグ
        content = soup.find('div', class_='topics-detail-content') or soup.find('article') or soup.find('main')
        return content.get_text(separator="\n", strip=True) if content else "本文の取得に失敗しました。"
    except:
        return "記事取得エラー"

def create_rss():
    # 碧さんが見つけてくれた黄金のURL
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス (API直撃版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("発見したAPIエンドポイントから直接データを取得しています")
    fg.language('ja')

    print(f"--- APIアクセス開始: {datetime.datetime.now()} ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://q-portal.riken.jp/",
    }

    try:
        res = requests.get(api_url, headers=headers, timeout=15)
        res.raise_for_status()
        
        # APIのレスポンス（JSON）を解析
        data = res.json()
        
        # APIの構造に合わせて記事リストを抽出
        # 通常、'data' や 'list' といったキーの中に記事が入っています
        # 碧さんのインスペクタで見た構造に合わせて調整が必要な場合があります
        articles = data.get('data', []) if isinstance(data, dict) else data

        print(f"成功: {len(articles)} 件の記事を見つけました。")

        for item in articles[:10]: # 最新10件を取得
            title = item.get('title', '無題')
            article_id = item.get('id')
            article_url = f"https://q-portal.riken.jp/topics/{article_id}"
            
            print(f"本文取得中: {title}")
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=article_url)
            
            # APIにはタイトルしかないので、本文は詳細ページをスクレイピング
            fe.description(get_article_body(article_url))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("成功: feed.xml を更新完了！")

    except Exception as e:
        print(f"エラー発生: {e}")

if __name__ == "__main__":
    create_rss()
