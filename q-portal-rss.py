import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time

def get_article_body(url):
    """詳細ページから本文を抽出"""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    try:
        time.sleep(1)
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Q-Portalの本文が含まれるタグ
        content = soup.find('div', class_='topics-detail-content') or soup.find('article') or soup.find('main')
        return content.get_text(separator="\n", strip=True) if content else "本文なし"
    except:
        return "取得エラー"

def create_rss():
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス (API確定版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("APIから正確にデータを取得し、全文を配信しています")
    fg.language('ja')

    print(f"--- APIアクセス開始: {datetime.datetime.now()} ---")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://q-portal.riken.jp",
        "Referer": "https://q-portal.riken.jp/",
        "Content-Type": "application/json",
    }

    try:
        # 碧さんが見つけた黄金のURLにPOSTリクエスト
        res = requests.post(api_url, headers=headers, json={}, timeout=15)
        res.raise_for_status()
        
        root_data = res.json()
        
        # 【ここを修正】 JSONの階層を正しく辿る
        # root['data']['topics'] の中に記事のリストがある
        articles = root_data.get('data', {}).get('topics', [])

        print(f"成功: {len(articles)} 件の記事リストを解析対象にします。")

        # 取得できた記事をループ
        for item in articles[:10]: # 最新10件
            title = item.get('title', '無題')
            article_id = item.get('id')
            # 実際のURL形式に合わせる
            article_url = f"https://q-portal.riken.jp/topics/{article_id}"
            
            print(f"全文取得中: {title}")
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=article_url)
            
            # 本文を詳細ページから取得
            fe.description(get_article_body(article_url))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("成功: feed.xml の生成が完了しました！")

    except Exception as e:
        print(f"エラー発生: {e}")
        import traceback
        traceback.print_exc() # 詳細なエラー場所を表示

if __name__ == "__main__":
    create_rss()
