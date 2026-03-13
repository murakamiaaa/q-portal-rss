import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time

def get_real_full_text(session, article_id):
    """3つの異なるAPIルートを試して、本文を救出する"""
    # 候補1: エディター用詳細API (ja)
    # 候補2: 公開用データAPI (Next.jsデータ)
    # 候補3: 通常のHTML解析
    
    urls = [
        f"https://q-portal-editor.riken.jp/api/v1/ja/topics/{article_id}",
        f"https://q-portal-editor.riken.jp/api/v1/topics/{article_id}",
    ]
    
    for url in urls:
        try:
            time.sleep(1)
            res = session.get(url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                # JSONの中から「最も長い文字列」を本文と断定して抜く
                # (理研のAPI構造 data -> topic -> content を想定)
                content = data.get('data', {}).get('topic', {}).get('content', '')
                if not content:
                    # 構造が違う場合、全探索
                    import json
                    dump = json.dumps(data, ensure_ascii=False)
                    import re
                    matches = re.findall(r'"([^"]{500,})"', dump)
                    if matches: content = matches[0]
                
                if content and len(content) > 300:
                    return BeautifulSoup(content, 'html.parser').get_text(separator="\n", strip=True)
        except:
            continue
    return None

def create_rss():
    list_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 全文 (Ultimate)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("APIの深層を同期して全文を抽出中")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"})

    try:
        res = session.post(list_url, json={}, timeout=15)
        articles = res.json().get('data', {}).get('topics', [])
        print(f"--- 最終ミッション開始: {len(articles)}件 ---")

        for item in articles[:10]:
            title = item.get('title', '無題')
            article_id = item.get('id')
            print(f"解析中: {title}")
            
            full_text = get_real_full_text(session, article_id)
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=f"https://q-portal.riken.jp/topics/{article_id}")
            
            if full_text:
                print(f"  -> 🎉 全文取得成功! ({len(full_text)}文字)")
                fe.description(full_text)
            else:
                print(f"  -> 💀 全文取得失敗... 概要のみ")
                fe.description(item.get('description', '全文取得失敗'))

            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 完了！")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    create_rss()