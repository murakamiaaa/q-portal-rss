import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json
import re

def extract_dense_text(html):
    """HTMLの中から最も文章密度が高い（＝本文らしい）場所を特定する"""
    soup = BeautifulSoup(html, 'html.parser')
    
    # 1. まずはHTML内の <script> 内にあるJSONを全スキャン
    scripts = soup.find_all('script')
    for script in scripts:
        if script.string and ('{' in script.string):
            # Unicodeエスケープをデコードして日本語にする
            try:
                content = script.string.encode().decode('unicode-escape')
                # 300文字以上の日本語の塊を正規表現で探す
                matches = re.findall(r'([^"{}]{300,})', content)
                for m in matches:
                    if '理研' in m:
                        return BeautifulSoup(m, 'html.parser').get_text(separator="\n", strip=True)
            except:
                continue

    # 2. 予備：HTMLタグの中で文字数が多いものを探す（広告やナビを除外）
    best_text = ""
    for tag in soup.find_all(['div', 'section', 'article']):
        # 不要なタグを除外
        if tag.parent.name in ['header', 'footer', 'nav']: continue
        
        # 子要素にさらにdivがない、末端に近い長いテキストを持つタグを優先
        current_text = tag.get_text(separator="\n", strip=True)
        if len(current_text) > len(best_text):
            best_text = current_text
            
    return best_text if len(best_text) > 200 else None

def create_rss():
    # 碧さんが見つけた黄金のAPI
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 全文配信 (Density Scan版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("文章密度解析により、構造変化に強い全文抽出を行っています")
    fg.language('ja')

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"})

    try:
        res = session.post(api_url, json={}, timeout=15)
        articles = res.json().get('data', {}).get('topics', [])
        print(f"--- 抽出開始: {len(articles)}件 ---")

        for item in articles[:10]:
            title = item.get('title', '無題')
            url = f"https://q-portal.riken.jp/topics/{item.get('id')}"
            print(f"解析中: {title}")
            
            time.sleep(1) # 礼儀
            detail_res = session.get(url, timeout=10)
            
            # 高密度テキスト抽出エンジンを回す
            full_text = extract_dense_text(detail_res.text)
            
            fe = fg.add_entry()
            fe.id(url)
            fe.title(title)
            fe.link(href=url)
            
            if full_text:
                print(f"  -> 成功! ({len(full_text)}文字)")
                fe.description(full_text)
            else:
                print(f"  -> 失敗... 概要を格納")
                fe.description(item.get('description', '本文取得失敗'))

            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 feed.xml 更新完了！")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    create_rss()