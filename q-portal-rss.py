import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json
import re

def get_best_content(session, item):
    """あらゆる手段を尽くして、その記事の『真の全文』を特定する"""
    numeric_id = item.get('id')
    topic_id = item.get('topic_id')
    article_url = f"https://q-portal.riken.jp/topics/{numeric_id}"
    
    print(f"\n--- 解析中: {item.get('title')} (TopicID: {topic_id}) ---")
    
    candidates = []

    # ルート1: Topic ID を使った詳細APIへのリベンジ
    if topic_id:
        try:
            api_url = f"https://q-portal-editor.riken.jp/api/v1/ja/topics/{topic_id}"
            res = session.get(api_url, timeout=10)
            if res.status_code == 200:
                data = res.json()
                # JSONの中から最も長い文字列を探す
                def find_longest(obj):
                    longest = ""
                    if isinstance(obj, str): return obj
                    if isinstance(obj, dict):
                        for v in obj.values():
                            cand = find_longest(v)
                            if len(cand) > len(longest): longest = cand
                    elif isinstance(obj, list):
                        for i in obj:
                            cand = find_longest(i)
                            if len(cand) > len(longest): longest = cand
                    return longest
                
                body = find_longest(data)
                if len(body) > 500:
                    print(f"  [API] 全文取得に成功! ({len(body)}文字)")
                    candidates.append(body)
        except: pass

    # ルート2: HTML内の全スクリプトタグからJSONを解析
    try:
        res = session.get(article_url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        for script in soup.find_all('script'):
            if script.string and ('{' in script.string):
                # 1000文字以上の「日本語を含む」塊を正規表現で探す
                matches = re.findall(r'"([^"]{1000,})"', script.string)
                for m in matches:
                    try:
                        # Unicodeエスケープを解除
                        decoded = m.encode().decode('unicode-escape')
                        if '理研' in decoded:
                            candidates.append(decoded)
                    except: continue
        
        # ルート3: 最終手段、HTMLのタグから直接
        for tag in soup.find_all(['div', 'article', 'section']):
            text = tag.get_text(separator="\n", strip=True)
            if len(text) > 800:
                candidates.append(text)
    except: pass

    if candidates:
        # 最も長いものを採用し、HTMLタグを掃除
        best = max(candidates, key=len)
        clean_text = BeautifulSoup(best, 'html.parser').get_text(separator="\n", strip=True)
        return clean_text
    
    # 全滅した場合は、検索APIの概要を返す
    return item.get('description', '全文の取得に失敗しました。')

def create_rss():
    list_api = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal (真・全文確定版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("複数の抽出ルートを並列実行し、真の全文を特定しています")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"})

    try:
        res = session.post(list_api, json={}, timeout=15)
        articles = res.json().get('data', {}).get('topics', [])
        print(f"--- 抽出開始: {len(articles)}件 ---")

        for item in articles[:10]:
            title = item.get('title', '無題')
            fe = fg.add_entry()
            fe.id(str(item.get('id')))
            fe.title(title)
            fe.link(href=f"https://q-portal.riken.jp/topics/{item.get('id')}")
            
            # 抽出エンジンを回す
            content = get_best_content(session, item)
            fe.description(content)
            
            # 日付設定
            date_str = item.get('release_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            fe.pubDate(datetime.datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("\n🎉 feed.xml の生成が完了しました！")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    create_rss()