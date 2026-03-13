import requests
from bs4 import BeautifulSoup # 追加
from feedgen.feed import FeedGenerator
import datetime
import time # 追加

def get_article_body(url):
    """記事のURLから本文を抽出する関数"""
    try:
        res = requests.get(url, timeout=10)
        res.raise_for_status()
        # HTMLを解析
        soup = BeautifulSoup(res.text, 'lxml')
        
        # Q-Portalの本文が入っているタグを探す
        # ※実際のHTML構造に合わせて調整が必要ですが、一般的には main や article タグ内
        content = soup.find('main') or soup.find('article')
        
        if content:
            # 余計なスクリプトやスタイルを除去してテキストだけ返す
            return content.get_text(separator="\n", strip=True)
        return "本文の取得に失敗しました。"
    except Exception:
        return "記事へのアクセスに失敗しました。"

def create_rss():
    json_url = "https://q-portal.riken.jp/data/topics.json"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス (全文配信)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("量子コンピュータの最新情報を本文込みで自動取得しています")
    fg.language('ja')

    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
        res = requests.get(json_url, headers=headers)
        res.raise_for_status()
        articles = res.json()

        # 最新5件に絞る（サーバーへの負荷を考えて最初は少なめに）
        for item in articles[:5]:
            article_url = f"https://q-portal.riken.jp/topics/{item['id']}"
            
            fe = fg.add_entry()
            fe.id(str(item['id']))
            fe.title(item['title'])
            fe.link(href=article_url)
            
            # --- ここで本文を取得！ ---
            print(f"Fetching: {item['title']}")
            body_text = get_article_body(article_url)
            fe.description(body_text) # RSSの本文としてセット
            # ----------------------
            
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))
            
            # 連続アクセスでサーバーに迷惑をかけないよう、1秒休む（礼儀）
            time.sleep(1)
            
    except Exception as e:
        print(f"Error: {e}")

    fg.rss_file('feed.xml')

if __name__ == "__main__":
    create_rss()

