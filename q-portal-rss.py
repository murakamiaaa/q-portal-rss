import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time

def clean_html(raw_html):
    """HTMLタグを掃除して綺麗なテキストにする"""
    if not raw_html:
        return "本文なし"
    # BeautifulSoupでタグを除去
    soup = BeautifulSoup(raw_html, 'html.parser')
    return soup.get_text(separator="\n", strip=True)

def create_rss():
    # 碧さんが見つけた「黄金の検索API」
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス (Complete Edition)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("検索APIから直接本文データを抽出しているため、高速かつ正確です")
    fg.language('ja')

    print(f"--- 全データ直接抽出ミッション開始: {datetime.datetime.now()} ---")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://q-portal.riken.jp",
        "Referer": "https://q-portal.riken.jp/",
    }

    try:
        # 1. 検索APIを叩く
        res = requests.post(api_url, headers=headers, json={}, timeout=15)
        res.raise_for_status()
        data = res.json()
        
        # 記事リストを特定
        articles = data.get('data', {}).get('topics', [])
        print(f"成功: {len(articles)} 件のデータを処理します。")

        # 最新10件を処理
        for item in articles[:10]:
            title = item.get('title', '無題')
            article_id = item.get('id')
            article_url = f"https://q-portal.riken.jp/topics/{article_id}"
            
            # 【ここが重要！】詳細APIを叩かず、itemの中にある description を使う
            content_raw = item.get('description', '')
            
            # もし description が空なら、念のため他のキーも探す
            if not content_raw:
                content_raw = item.get('content', '')
            
            content_clean = clean_html(content_raw)
            
            print(f"記事を格納中: {title} (文字数: {len(content_clean)})")
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=article_url)
            fe.description(content_clean)
            
            # 日付処理（APIの release_date を使用）
            date_str = item.get('release_date', datetime.datetime.now().strftime('%Y-%m-%d'))
            try:
                pub_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
            except:
                pub_date = datetime.datetime.now(datetime.timezone.utc)
            fe.pubDate(pub_date)

        fg.rss_file('feed.xml')
        print("🎉 成功: feed.xml が真の完成を迎えました！")

    except Exception as e:
        print(f"エラー発生: {e}")

if __name__ == "__main__":
    create_rss()