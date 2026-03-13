import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json

def find_content_in_dict(obj, key_name='content'):
    """辞書の中から指定したキー(content)を再帰的に探し出す関数"""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key_name and isinstance(v, str) and len(v) > 50: # 50文字以上の文字列なら本文とみなす
                return v
            result = find_content_in_dict(v, key_name)
            if result: return result
    elif isinstance(obj, list):
        for item in obj:
            result = find_content_in_dict(item, key_name)
            if result: return result
    return None

def get_article_body(session, url):
    """詳細ページのJSONから本文を自動探索して抽出する"""
    try:
        time.sleep(1)
        res = session.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 埋め込みJSONを探す
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            data = json.loads(next_data.string)
            # 1. 'content' という名前のデータを全自動で探す
            raw_content = find_content_in_dict(data, 'content')
            # 2. もしなければ 'body' という名前で探す
            if not raw_content:
                raw_content = find_content_in_dict(data, 'body')
            
            if raw_content:
                # HTMLタグを掃除してテキストにする
                return BeautifulSoup(raw_content, 'html.parser').get_text(separator="\n", strip=True)

        return "本文の抽出に失敗しました。構造が想定と異なります。"
    except Exception as e:
        return f"エラー: {e}"

def create_rss():
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス (全文配信・完成版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("APIと全自動解析を組み合わせて全文を配信中")
    fg.language('ja')

    print(f"--- 最終ミッション開始: {datetime.datetime.now()} ---")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://q-portal.riken.jp",
        "Referer": "https://q-portal.riken.jp/",
    })

    try:
        # 記事リストを取得
        res = session.post(api_url, json={}, timeout=15)
        articles = res.json().get('data', {}).get('topics', [])
        print(f"成功: {len(articles)} 件の記事を解析します。")

        # 最新10件を取得
        for item in articles[:10]:
            title = item.get('title', '無題')
            article_url = f"https://q-portal.riken.jp/topics/{item.get('id')}"
            print(f"解析中: {title}")
            
            fe = fg.add_entry()
            fe.id(article_url)
            fe.title(title)
            fe.link(href=article_url)
            fe.description(get_article_body(session, article_url))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 feed.xml が本当の完成を迎えました！")

    except Exception as e:
        print(f"致命的エラー: {e}")

if __name__ == "__main__":
    create_rss()