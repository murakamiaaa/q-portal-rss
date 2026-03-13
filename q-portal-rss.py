import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import sys

def get_article_body(url):
    """記事の詳細ページから本文を抽出する関数"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        # サーバーに負荷をかけないよう、取得前に少し待機
        time.sleep(1)
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        
        # HTMLの解析（高速なlxmlを使用。入っていない場合は 'html.parser' に自動で切り替わります）
        try:
            soup = BeautifulSoup(res.text, 'lxml')
        except:
            soup = BeautifulSoup(res.text, 'html.parser')
        
        # Q-Portalの本文が含まれる可能性が高いタグを順番に探す
        # サイトの構造に合わせて、より具体的なクラス名を追加しています
        content = (
            soup.find('div', class_='topics-detail-content') or 
            soup.find('div', class_='p-topics-detail__body') or
            soup.find('article') or 
            soup.find('main')
        )
        
        if content:
            # 不要なタグ（スクリプトやボタンなど）があればここで除去
            for s in content(['script', 'style', 'nav', 'header', 'footer']):
                s.decompose()
            return content.get_text(separator="\n", strip=True)
        
        return "本文の抽出に失敗しました（該当するタグが見つかりません）。"
    
    except Exception as e:
        return f"記事の取得中にエラーが発生しました: {e}"

def create_rss():
    json_url = "https://q-portal.riken.jp/data/topics.json"
    
    # 1. FeedGeneratorの初期設定
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス (全文配信版)")
    fg.author({'name': 'Aoi Murakami', 'email': 'murakami@example.com'}) # 碧さんの名前をセット
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("量子コンピュータポータルサイト「Q-Portal」の新着情報を本文込みで配信中")
    fg.language('ja')

    # 2. JSONデータの取得（ヘッダーを強化）
    print(f"--- 実行開始: {datetime.datetime.now()} ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://q-portal.riken.jp/topics?lang=ja",
        "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
    }

    try:
        print(f"JSONを取得中: {json_url}")
        res = requests.get(json_url, headers=headers, timeout=15)
        
        # デバッグ情報：ステータスコードを表示
        print(f"HTTP Status Code: {res.status_code}")
        
        if res.status_code != 200:
            print("エラー: サーバーから正常なレスポンスが返ってきませんでした。")
            print(f"Response Body (first 500 chars): {res.text[:500]}")
            res.raise_for_status()

        articles = res.json()
        print(f"成功: {len(articles)} 件の記事を見つけました。")

        # 3. 記事ごとに詳細を取得（最新5件に制限）
        for item in articles[:5]:
            title = item.get('title', '無題')
            article_id = item.get('id')
            article_url = f"https://q-portal.riken.jp/topics/{article_id}"
            
            print(f"本文を取得中: {title}")
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=article_url)
            
            # 詳細ページから本文を取得してセット
            content_body = get_article_body(article_url)
            fe.description(content_body)
            
            # 日付の設定（JSONに日付がない場合は現在時刻を使用）
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        # 4. ファイル書き出し
        fg.rss_file('feed.xml')
        print("成功: feed.xml を更新しました。")

    except requests.exceptions.JSONDecodeError:
        print("エラー: 取得したデータがJSON形式ではありませんでした。")
        print(f"受信データの内容: {res.text[:500]}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    create_rss()
