`import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json

def find_longest_string(obj):
    """辞書やリストの中から、最も長い文字列（＝本文）を探し出す"""
    longest = ""
    
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, dict):
        for v in obj.values():
            res = find_longest_string(v)
            if len(res) > len(longest):
                longest = res
    elif isinstance(obj, list):
        for item in obj:
            res = find_longest_string(item)
            if len(res) > len(longest):
                longest = res
    return longest

def get_article_body(session, url):
    """詳細ページのJSONから、最も本文らしい長い文字列を引っこ抜く"""
    try:
        time.sleep(1)
        res = session.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. 埋め込みJSON (__NEXT_DATA__) を探す
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            data = json.loads(next_data.string)
            # JSON全体の中から「最も長い文字列」を抽出
            raw_content = find_longest_string(data)
            
            # 200文字以上なら本文とみなす（短すぎたら別のものを探す）
            if len(raw_content) > 200:
                # HTMLタグが混じっている場合を考慮して掃除
                return BeautifulSoup(raw_content, 'html.parser').get_text(separator="\n", strip=True)

        # 2. 予備：もしJSONがダメなら、HTML内の長いdivを探す
        for tag in soup.find_all(['div', 'article']):
            if len(tag.get_text()) > 500: # 500文字以上のブロックがあればそれ
                return tag.get_text(separator="\n", strip=True)

        return "本文の特定に失敗しました。サイト構造が大幅に特殊な可能性があります。"
    except Exception as e:
        return f"エラー: {e}"

def create_rss():
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス (全文配信・完全版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("AIアルゴリズム的な最長文字列抽出により、全文を安定配信中")
    fg.language('ja')

    print(f"--- 最終ミッション実行中: {datetime.datetime.now()} ---")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://q-portal.riken.jp",
        "Referer": "https://q-portal.riken.jp/",
    })

    try:
        # APIからリストを取得
        res = session.post(api_url, json={}, timeout=15)
        articles = res.json().get('data', {}).get('topics', [])
        print(f"成功: {len(articles)} 件の記事を解析します。")

        for item in articles[:10]:
            title = item.get('title', '無題')
            article_url = f"https://q-portal.riken.jp/topics/{item.get('id')}"
            print(f"全文を抽出中: {title}")
            
            fe = fg.add_entry()
            fe.id(article_url)
            fe.title(title)
            fe.link(href=article_url)
            fe.description(get_article_body(session, article_url))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 feed.xml の完全生成に成功しました！")

    except Exception as e:
        print(f"エラー発生: {e}")

if __name__ == "__main__":
    create_rss()