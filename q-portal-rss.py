import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json

def get_article_body(session, url):
    """セッションを引き継いで本文を取得"""
    try:
        time.sleep(1)
        res = session.get(url, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        # 本文のタグ（Q-Portalの実際の構造に合わせる）
        content = soup.find('div', class_='topics-detail-content') or soup.find('article') or soup.body
        return content.get_text(separator="\n", strip=True) if content else "本文なし"
    except:
        return "取得エラー"

def create_rss():
    # JSONの直接URL（ここが源泉です）
    json_url = "https://q-portal.riken.jp/data/topics.json"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 全文配信版 (Session方式)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("ブラウザセッションを模倣してデータを直接取得中")

    print(f"--- 実行開始: {datetime.datetime.now()} ---")

    # セッションを開始（クッキー等を自動管理）
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://q-portal.riken.jp/topics?lang=ja",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    })

    try:
        # 1. まずはトップページにアクセスして「挨拶（クッキー取得）」
        print("トップページに挨拶中...")
        session.get("https://q-portal.riken.jp/", timeout=10)
        
        # 2. そのままの勢いでJSONを取得
        print(f"JSONデータを取得中: {json_url}")
        res = session.get(json_url, timeout=15)
        
        print(f"Status Code: {res.status_code}")
        
        # もしJSONとして解析できなかったらHTMLとして中身を表示（デバッグ用）
        try:
            articles = res.json()
            print(f"成功: {len(articles)} 件の記事をJSONから発見しました。")
        except:
            print("警告: JSONとして読み込めませんでした。返ってきた内容の一部を表示します。")
            print(res.text[:300])
            return

        # 3. 記事をRSSに追加
        for item in articles[:5]:
            title = item.get('title', '無題')
            article_url = f"https://q-portal.riken.jp/topics/{item.get('id')}"
            print(f"処理中: {title}")
            
            fe = fg.add_entry()
            fe.id(article_url)
            fe.title(title)
            fe.link(href=article_url)
            fe.description(get_article_body(session, article_url))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("成功: feed.xml を生成しました。")

    except Exception as e:
        print(f"エラー発生: {e}")

if __name__ == "__main__":
    create_rss()
