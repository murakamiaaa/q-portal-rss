import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json

def get_article_body_from_api(session, article_id):
    """APIの中身を徹底的にスキャンして、本文らしいものを探し出す"""
    detail_api_url = f"https://q-portal-editor.riken.jp/api/v1/ja/topics/{article_id}"
    
    try:
        time.sleep(1)
        res = session.get(detail_api_url, timeout=10)
        res.raise_for_status()
        data = res.json()

        # 【デバッグ用】GitHubのログに、APIが返してきたデータの「キー」をすべて書き出す
        print(f"--- API解析中 (ID: {article_id}) ---")
        # 辞書の中身をダンプして構造を丸裸にします
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000]) 

        # 1. 可能性の高い場所を順番にチェック
        # パターンA: data -> topic -> content (前回の予想)
        # パターンB: data -> detail -> content
        # パターンC: data -> content
        # パターンD: topic -> content
        
        candidates = [
            data.get('data', {}).get('topic', {}).get('content'),
            data.get('data', {}).get('detail', {}).get('content'),
            data.get('data', {}).get('content'),
            data.get('topic', {}).get('content'),
            data.get('content')
        ]

        for content in candidates:
            if content and isinstance(content, str) and len(content) > 20:
                return BeautifulSoup(content, 'html.parser').get_text(separator="\n", strip=True)

        return "APIには到達しましたが、本文キーが見つかりません。ログのJSON構造を確認してください。"
        
    except Exception as e:
        return f"APIアクセスエラー: {e}"

def create_rss():
    list_api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 全文配信 (API Debug Edition)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("APIの内部構造を解析しながら全文を抽出しています")
    fg.language('ja')

    print(f"--- API解析ミッション開始: {datetime.datetime.now()} ---")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://q-portal.riken.jp",
        "Referer": "https://q-portal.riken.jp/",
    })

    try:
        res = session.post(list_api_url, json={}, timeout=15)
        articles = res.json().get('data', {}).get('topics', [])
        
        print(f"成功: {len(articles)} 件の記事を特定。")

        # 最初の3件だけでテスト（ログが埋まらないように）
        for item in articles[:3]:
            title = item.get('title', '無題')
            article_id = item.get('id')
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=f"https://q-portal.riken.jp/topics/{article_id}")
            fe.description(get_article_body_from_api(session, article_id))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 feed.xml を仮更新しました。")

    except Exception as e:
        print(f"致命的エラー: {e}")

if __name__ == "__main__":
    create_rss()