import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json

def collect_all_long_strings(obj, min_length=100):
    """辞書やリストの中から、一定以上の長さの文字列をすべて集める"""
    texts = []
    if isinstance(obj, str):
        if len(obj) >= min_length:
            texts.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            texts.extend(collect_all_long_strings(v, min_length))
    elif isinstance(obj, list):
        for item in obj:
            texts.extend(collect_all_long_strings(item, min_length))
    return texts

def get_article_body(session, url):
    """詳細ページのJSONから、すべての長文ブロックを拾い集めて結合する"""
    try:
        time.sleep(1)
        res = session.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 1. 埋め込みJSON (__NEXT_DATA__) を探す
        next_data = soup.find('script', id='__NEXT_DATA__')
        if next_data:
            data = json.loads(next_data.string)
            # JSONの中から100文字以上の文字列をすべて集める
            all_texts = collect_all_long_strings(data, min_length=100)
            
            # 重複を除去しながら結合（順序を維持）
            seen = set()
            unique_texts = []
            for t in all_texts:
                if t not in seen:
                    unique_texts.append(t)
                    seen.add(t)
            
            if unique_texts:
                # 結合してHTMLタグを掃除
                full_html = "\n\n".join(unique_texts)
                return BeautifulSoup(full_html, 'html.parser').get_text(separator="\n", strip=True)

        # 2. 予備：HTMLの特定タグから直接抽出（JSONがダメな場合）
        body_tag = soup.find('div', class_='topics-detail-content') or soup.find('article')
        if body_tag:
            return body_tag.get_text(separator="\n", strip=True)

        return "本文の自動抽出に失敗しました。サイト構造を再確認してください。"
    except Exception as e:
        return f"エラー: {e}"

def create_rss():
    # 碧さんが見つけた黄金のURL
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 全文配信 (Ultimate Edition)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("AIアルゴリズムによる全自動テキスト結合により、全文を安定配信中")
    fg.language('ja')

    print(f"--- 最終ミッション実行中: {datetime.datetime.now()} ---")
    
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
        print("🎉 成功: feed.xml の完全生成に成功しました！")

    except Exception as e:
        print(f"エラー発生: {e}")

if __name__ == "__main__":
    create_rss()