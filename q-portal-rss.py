import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json

def get_content_with_logging(session, article_id):
    """詳細データを取得し、構造をログに詳しく書き出す"""
    # 候補となるAPIエンドポイント
    url = f"https://q-portal-editor.riken.jp/api/v1/ja/topics/{article_id}"
    
    try:
        time.sleep(1)
        res = session.get(url, timeout=10)
        if res.status_code == 200:
            data = res.json()
            
            # 【重要】データ構造を再帰的にスキャンして、100文字以上の文字列をすべて集める
            collected_texts = []
            def scanner(obj):
                if isinstance(obj, str):
                    if len(obj) > 100: collected_texts.append(obj)
                elif isinstance(obj, dict):
                    for v in obj.values(): scanner(v)
                elif isinstance(obj, list):
                    for i in obj: scanner(i)
            
            scanner(data)
            
            if collected_texts:
                # 最も長いものを本文とみなす
                full_text = max(collected_texts, key=len)
                print(f"  -> 🎉 抽出成功! ({len(full_text)}文字)")
                return BeautifulSoup(full_text, 'html.parser').get_text(separator="\n", strip=True)
        
        print(f"  -> 💀 API(ID:{article_id}) から長文が見つかりませんでした")
        return None
    except Exception as e:
        print(f"  -> ⚠️ 通信エラー: {e}")
        return None

def create_rss():
    list_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal (完全全文版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("データ構造を全スキャンして、隠された全文を抽出しています")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"})

    try:
        res = session.post(list_url, json={}, timeout=15)
        articles = res.json().get('data', {}).get('topics', [])
        print(f"--- 全文捜索開始: {len(articles)}件 ---")

        for item in articles[:5]: # テスト用にまずは5件
            title = item.get('title', '無題')
            article_id = item.get('id')
            print(f"解析中: {title} (ID: {article_id})")
            
            full_text = get_content_with_logging(session, article_id)
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=f"https://q-portal.riken.jp/topics/{article_id}")
            
            if full_text:
                fe.description(full_text)
            else:
                fe.description(item.get('description', '全文取得失敗'))

            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 完了！")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    create_rss()