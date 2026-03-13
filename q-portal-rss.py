import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time

def clean_html(raw_html):
    """HTMLタグを除去し、実体参照（&nbsp;等）を掃除する"""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, 'html.parser')
    # 不要なタグがあればここで削除可能
    return soup.get_text(separator="\n", strip=True)

def create_rss():
    # 碧さんが見つけた「黄金の検索API」
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス (検索API抽出版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("検索結果に含まれる description フィールドから本文を抽出しています")
    fg.language('ja')

    print(f"--- 抽出ミッション開始: {datetime.datetime.now()} ---")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://q-portal.riken.jp",
        "Referer": "https://q-portal.riken.jp/",
    }

    try:
        # 検索APIを叩く（1回で675件分のデータが手に入る）
        res = requests.post(api_url, headers=headers, json={}, timeout=15)
        res.raise_for_status()
        data = res.json()
        
        articles = data.get('data', {}).get('topics', [])
        print(f"成功: {len(articles)} 件のデータを特定しました。")

        # 最新10件をRSSに格納
        for item in articles[:10]:
            title = item.get('title', '無題')
            article_id = item.get('id')
            article_url = f"https://q-portal.riken.jp/topics/{article_id}"
            
            # 【ここがポイント】詳細APIを叩かず、検索結果の description を使う
            raw_content = item.get('description', '')
            clean_content = clean_html(raw_content)
            
            print(f"格納中: {title} ({len(clean_content)}文字)")
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=article_url)
            fe.description(clean_content if clean_content else "本文の取得に失敗しました。")
            
            # 日付（release_date）の設定
            date_str = item.get('release_date')
            if date_str:
                dt = datetime.datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=datetime.timezone.utc)
                fe.pubDate(dt)
            else:
                fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("成功: feed.xml の生成が完了しました！")

    except Exception as e:
        print(f"エラー発生: {e}")

if __name__ == "__main__":
    create_rss()