import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import re

def aggressive_extract(html):
    """HTML内のあらゆる場所から、最も『本文らしい』長い文章を力技で探す"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. 1000文字以上のテキストを持つタグを片っ端から探す
    for tag in soup.find_all(['div', 'section', 'article']):
        # スクリプトやスタイルは除外
        if tag.name in ['script', 'style']: continue
        text = tag.get_text(separator="\n", strip=True)
        if len(text) > 1000:
            return text

    # 2. JSON風の文字列の中に隠れている長い日本語を正規表現で抜く
    # (Unicodeエスケープ \uXXXX も考慮)
    matches = re.findall(r'"([^"]{1000,})"', html)
    for m in matches:
        try:
            decoded = m.encode().decode('unicode-escape')
            if '理研' in decoded or '研究' in decoded:
                return BeautifulSoup(decoded, 'html.parser').get_text(separator="\n", strip=True)
        except:
            continue
            
    return None

def create_rss():
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal (真・全文抽出版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("最深部のテキストデータを走査して抽出しています")

    print(f"--- 深層解析開始: {datetime.datetime.now()} ---")
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}

    try:
        res = requests.post(api_url, headers=headers, json={}, timeout=15)
        articles = res.json().get('data', {}).get('topics', [])
        
        for item in articles[:10]:
            title = item.get('title', '無題')
            url = f"https://q-portal.riken.jp/topics/{item.get('id')}"
            print(f"解析中: {title}")
            
            time.sleep(1)
            detail_res = requests.get(url, headers=headers, timeout=15)
            
            # 究極の抽出ロジック
            full_content = aggressive_extract(detail_res.text)
            
            # 全文が取れなければ、検索APIの概要を使いつつ (全文取得失敗) と表示する
            if full_content:
                description = full_content
                print(f"  -> 全文取得成功! ({len(description)}文字)")
            else:
                description = f"【全文取得に失敗しました。概要のみ表示します】\n\n{item.get('description', '')}"
                print(f"  -> 全文取得失敗... (概要のみ格納)")

            fe = fg.add_entry()
            fe.id(url)
            fe.title(title)
            fe.link(href=url)
            fe.description(description)
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 feed.xml 更新完了")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    create_rss()