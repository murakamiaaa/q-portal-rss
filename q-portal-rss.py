import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json
import re

def get_article_body(url):
    """記事の本文を取得（ここは以前のものを強化）"""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    try:
        time.sleep(1)
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        # Q-Portalの本文タグ候補
        content = soup.find('div', class_='topics-detail-content') or soup.find('article') or soup.find('main')
        return content.get_text(separator="\n", strip=True) if content else "本文の取得に失敗しました。"
    except:
        return "記事取得エラー"

def create_rss():
    # JSONファイルを直接叩くのではなく、人間が見る「トピックス一覧ページ」を叩きます
    target_url = "https://q-portal.riken.jp/topics?lang=ja"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 全文配信版 (HTML-JSON方式)")
    fg.link(href=target_url, rel='alternate')
    fg.description("HTML内に埋め込まれたデータを解析して配信中")

    print(f"--- 探索開始: {datetime.datetime.now()} ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }

    try:
        res = requests.get(target_url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')

        # 【重要】Next.jsなどのフレームワークがデータを埋め込む特別なタグを探す
        next_data = soup.find('script', id='__NEXT_DATA__')
        
        articles = []
        if next_data:
            print("DEBUG: __NEXT_DATA__ を発見しました。解析を開始します。")
            data = json.loads(next_data.string)
            # JSONの中から「記事リスト」が入っている深い階層を探り当てる（パスは推測）
            # Q-Portalの構造に合わせて、ここを調整します
            try:
                # 一般的なNext.jsのデータ配置場所
                articles_raw = data['props']['pageProps']['topics']
                for item in articles_raw:
                    articles.append({
                        'id': item.get('id'),
                        'title': item.get('title'),
                        'url': f"https://q-portal.riken.jp/topics/{item.get('id')}"
                    })
            except KeyError:
                print("DEBUG: 想定したJSON構造が見つかりませんでした。別の場所を探します。")

        # もし上の方法でダメなら、正規表現で強引にJSONっぽい部分を抜き出す
        if not articles:
            print("DEBUG: 強制スキャンを開始します。")
            pattern = re.compile(r'\"topics\":\s*(\[.*?\])', re.DOTALL)
            match = pattern.search(res.text)
            if match:
                articles_raw = json.loads(match.group(1))
                for item in articles_raw:
                    articles.append({
                        'id': item.get('id'),
                        'title': item.get('title'),
                        'url': f"https://q-portal.riken.jp/topics/{item.get('id')}"
                    })

        print(f"成功: {len(articles)} 件の記事を特定しました。")

        for item in articles[:5]:
            print(f"取得中: {item['title']}")
            fe = fg.add_entry()
            fe.id(item['url'])
            fe.title(item['title'])
            fe.link(href=item['url'])
            fe.description(get_article_body(item['url']))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("成功: feed.xml を更新しました。")

    except Exception as e:
        print(f"致命的なエラー: {e}")
        # エラー時にHTMLを少しだけ出力してヒントにする
        print(f"HTML冒頭: {res.text[:200]}")

if __name__ == "__main__":
    create_rss()
