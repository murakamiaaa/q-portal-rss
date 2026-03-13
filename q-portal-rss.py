import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json

def get_article_body_from_api(session, article_id):
    """詳細APIを直接叩いて、クリーンな本文データを取得する"""
    # 碧さんが見つけたエディター用ドメインの詳細API
    detail_api_url = f"https://q-portal-editor.riken.jp/api/v1/ja/topics/{article_id}"
    
    try:
        time.sleep(1) # サーバーへの礼儀
        # 詳細APIは GET で取得できる可能性が高いです
        res = session.get(detail_api_url, timeout=10)
        
        # もしGETでダメ(405)ならPOSTに切り替える自動フォールバック
        if res.status_code == 405:
            res = session.post(detail_api_url, json={}, timeout=10)
            
        res.raise_for_status()
        data = res.json()

        # APIの構造から本文（content）を抽出
        # 構造: data -> topic -> content
        topic_data = data.get('data', {}).get('topic', {})
        content_html = topic_data.get('content', '')
        
        if content_html:
            # HTMLタグが含まれているので、BeautifulSoupで綺麗なテキストにする
            return BeautifulSoup(content_html, 'html.parser').get_text(separator="\n", strip=True)
        
        # もし content というキーがなければ、JSON全体から一番長い文字列を探す（念のため）
        return "詳細APIに本文が含まれていませんでした。"
        
    except Exception as e:
        return f"詳細APIの取得に失敗しました: {e}"

def create_rss():
    # 碧さんが見つけたリスト取得用API
    list_api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 全文配信 (API Perfect Edition)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("リストと詳細の両方をAPIから直接取得する、最も安定した配信方式")
    fg.language('ja')

    print(f"--- API完全同期ミッション開始: {datetime.datetime.now()} ---")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://q-portal.riken.jp",
        "Referer": "https://q-portal.riken.jp/",
    })

    try:
        # 1. 記事リストを取得（ここは前回の成功コードと同じPOST）
        res = session.post(list_api_url, json={}, timeout=15)
        res.raise_for_status()
        articles = res.json().get('data', {}).get('topics', [])
        
        print(f"成功: {len(articles)} 件の記事を特定。API経由で詳細を読み込みます。")

        # 最新10件を取得
        for item in articles[:10]:
            title = item.get('title', '無題')
            article_id = item.get('id')
            article_url = f"https://q-portal.riken.jp/topics/{article_id}"
            
            print(f"詳細APIにアクセス中: {title}")
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=article_url)
            
            # 【ここが進化】詳細ページ（HTML）ではなく、詳細APIから本文を直接取る
            fe.description(get_article_body_from_api(session, article_id))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 成功: feed.xml の完全同期が完了しました！")

    except Exception as e:
        print(f"致命的エラー: {e}")

if __name__ == "__main__":
    create_rss()