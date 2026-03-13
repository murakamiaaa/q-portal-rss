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
        time.sleep(1)
        res = session.get(url, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. まずは通常のタグを探す（もしあれば）
        content_tag = soup.find('div', class_='topics-detail-content') or soup.find('article')
        if content_tag and len(content_tag.get_text(strip=True)) > 10:
            return content_tag.get_text(separator="\n", strip=True)

        # 2. 【本命】Next.js等の埋め込みJSON (__NEXT_DATA__) を探す
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        if next_data_script:
            data = json.loads(next_data_script.string)
            # JSONの中から本文(content)が入っている場所を探索
            # Q-Portalの構造: pageProps -> topic -> content
            try:
                content = data['props']['pageProps']['topic']['content']
                # HTMLタグが含まれている場合はBeautifulSoupでテキスト化
                return BeautifulSoup(content, 'html.parser').get_text(separator="\n", strip=True)
            except (KeyError, TypeError):
                pass

        # 3. 最終手段：正規表現でJSONっぽい構造から content の中身を抜く
        match = re.search(r'"content":"(.*?)"', res.text)
        if match:
            # unicodeエスケープされた文字を復元
            raw_content = match.group(1).encode().decode('unicode-escape')
            return BeautifulSoup(raw_content, 'html.parser').get_text(separator="\n", strip=True)

        return "本文の抽出に失敗しました（JavaScript実行が必要な可能性があります）。"

    except Exception as e:
        return f"取得エラー: {e}"

def create_rss():
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス (全文配信・完成版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("APIと個別ページ解析を組み合わせて全文を配信中")
    fg.language('ja')

    print(f"--- 最終処理開始: {datetime.datetime.now()} ---")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://q-portal.riken.jp",
        "Referer": "https://q-portal.riken.jp/",
        "Content-Type": "application/json",
    })

    try:
        # APIからリストを取得
        res = session.post(api_url, json={}, timeout=15)
        res.raise_for_status()
        root_data = res.json()
        articles = root_data.get('data', {}).get('topics', [])

        print(f"成功: {len(articles)} 件の記事を解析します。")

        for item in articles[:10]:
            title = item.get('title', '無題')
            article_id = item.get('id')
            article_url = f"https://q-portal.riken.jp/topics/{article_id}"
            
            print(f"全文を解析中: {title}")
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=article_url)
            
            # 強化した抽出関数を呼び出す
            fe.description(get_article_body(session, article_url))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 成功: feed.xml が真の完成を迎えました！")

    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    create_rss()
