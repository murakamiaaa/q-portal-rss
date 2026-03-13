import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json
import re

def get_article_body(session, url):
    """詳細ページのHTML内に隠されたJSONから本文を抽出する"""
    try:
        time.sleep(1) # 礼儀正しいスクレイピング
        res = session.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. Next.js等の埋め込みJSON (__NEXT_DATA__) を探す（これが本命）
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        if next_data_script:
            data = json.loads(next_data_script.string)
            try:
                # Q-Portalの構造: topic -> content の中身を狙い撃ち
                content_html = data['props']['pageProps']['topic']['content']
                # HTMLタグが混じっているので、テキストだけを綺麗に取り出す
                return BeautifulSoup(content_html, 'html.parser').get_text(separator="\n", strip=True)
            except (KeyError, TypeError):
                pass

        # 2. 予備：通常のタグで探す
        content_tag = soup.find('div', class_='topics-detail-content') or soup.find('article')
        if content_tag and len(content_tag.get_text(strip=True)) > 10:
            return content_tag.get_text(separator="\n", strip=True)

        return "本文の抽出に失敗しました（構造が変更された可能性があります）。"

    except Exception as e:
        return f"取得エラー: {e}"

def create_rss():
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス (全文配信・完全版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("APIと個別ページJSON解析を組み合わせて全文を配信中")
    fg.language('ja')

    print(f"--- 最終処理開始: {datetime.datetime.now()} ---")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://q-portal.riken.jp",
        "Referer": "https://q-portal.riken.jp/",
    })

    try:
        # APIからリストをPOSTで取得（碧さんが見つけた黄金のURL）
        res = session.post(api_url, json={}, timeout=15)
        res.raise_for_status()
        root_data = res.json()
        articles = root_data.get('data', {}).get('topics', [])

        print(f"成功: {len(articles)} 件の記事を解析対象にします。")

        # 最新10件の全文を取得
        for item in articles[:10]:
            title = item.get('title', '無題')
            article_id = item.get('id')
            article_url = f"https://q-portal.riken.jp/topics/{article_id}"
            
            print(f"全文を解析中: {title}")
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=article_url)
            
            # 強化した関数で本文を抽出
            fe.description(get_article_body(session, article_url))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 成功: feed.xml が真の完成を迎えました！")

    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    create_rss()
