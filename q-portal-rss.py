import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time

def get_real_body_from_api(session, topic_id):
    """碧さんが特定した真のAPIから、topic_bodyを直接取得する"""
    if not topic_id:
        return None
        
    # 碧さんが見つけ出した「真のURL」
    api_url = f"https://q-portal-editor.riken.jp/api/v1/ja/topics/{topic_id}"
    
    try:
        time.sleep(1) # サーバーへの礼儀
        res = session.get(api_url, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            
            # JSONの深い階層から、どんな構造でも確実に 'topic_body' を探し出す関数
            def find_topic_body(obj):
                if isinstance(obj, dict):
                    if 'topic_body' in obj and obj['topic_body']:
                        return obj['topic_body']
                    for v in obj.values():
                        result = find_topic_body(v)
                        if result: return result
                elif isinstance(obj, list):
                    for item in obj:
                        result = find_topic_body(item)
                        if result: return result
                return None
                
            body_html = find_topic_body(data)
            
            if body_html:
                # APIから返ってきたHTMLタグ（<br />等）を綺麗なテキストに変換
                clean_text = BeautifulSoup(body_html, 'html.parser').get_text(separator="\n", strip=True)
                print(f"  -> 🎉 本文抽出成功! ({len(clean_text)}文字)")
                return clean_text
                
        print("  -> 💀 APIは応答しましたが、topic_bodyが空でした")
        return None
        
    except Exception as e:
        print(f"  -> ⚠️ API通信エラー: {e}")
        return None

def create_rss():
    # リスト取得用API
    list_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal (完全フルテキスト配信)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("専用APIからtopic_bodyを直接同期する究極のRSSフィード")
    fg.language('ja')

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"})

    try:
        res = session.post(list_url, json={}, timeout=15)
        articles = res.json().get('data', {}).get('topics', [])
        print(f"--- 最終同期ミッション開始: {len(articles)}件 ---")

        for item in articles[:10]:
            title = item.get('title', '無題')
            article_id = item.get('id')
            topic_id = item.get('topic_id') # ここが最大の鍵！
            article_url = f"https://q-portal.riken.jp/topics/{article_id}"
            
            print(f"解析中: {title} (TopicID: {topic_id})")
            
            # 真のAPIを叩く
            full_text = get_real_body_from_api(session, topic_id)
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=article_url)
            
            if full_text:
                fe.description(full_text)
            else:
                fe.description(item.get('description', '本文の取得に失敗しました。'))

            # タイムゾーンを考慮した日付処理
            date_str = item.get('release_date')
            if date_str:
                dt = datetime.datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
                fe.pubDate(dt)
            else:
                fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 完璧な feed.xml の生成が完了しました！")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    create_rss()