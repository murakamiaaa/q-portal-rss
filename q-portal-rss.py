import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json # 追加
from urllib.parse import urljoin

def get_article_body(url):
    """詳細ページの本文を取得（ここは前回と同じ）"""
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
    try:
        time.sleep(1)
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        content = soup.find('div', class_='topics-detail-content') or soup.find('article') or soup.find('main')
        return content.get_text(separator="\n", strip=True) if content else "本文なし"
    except:
        return "取得エラー"

def create_rss():
    list_url = "https://q-portal.riken.jp/topics?lang=ja"
    base_url = "https://q-portal.riken.jp/"
    
    fg = FeedGenerator()
    fg.id(base_url)
    fg.title("Q-Portal 全文配信版 (Debug)")
    fg.link(href=list_url, rel='alternate')
    fg.description("デバッグ中: 記事が0件になる問題を調査中")

    print(f"--- 調査開始: {datetime.datetime.now()} ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    }

    try:
        res = requests.get(list_url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # --- デバッグ1: ページ内にどんなリンクがあるか最初の5つだけ出す ---
        all_links = soup.find_all('a', href=True)
        print(f"DEBUG: ページ全体のaタグ総数 = {len(all_links)}")
        for a in all_links[:10]:
            print(f"DEBUG: 見つけたリンク例 = {a['href']}")

        # --- デバッグ2: HTML内に埋め込まれたJSONデータ(Next.js等)がないか探す ---
        next_data = soup.find('script', id='__NEXT_DATA__')
        articles = []

        if next_data:
            print("DEBUG: __NEXT_DATA__ タグを発見しました！解析します。")
            data = json.loads(next_data.string)
            # ここでJSONの深い階層から記事を探す（サイト構造に依存）
            # 一般的なNext.jsのパターンで試行
            try:
                # サイトごとの構造に合わせてパスを掘る必要があります
                # とりあえずログにJSONの構造を一部出す
                print(f"DEBUG: JSONデータ構造のキー = {data.keys()}")
            except:
                pass

        # --- 従来の抽出方法（条件を少し緩くして再挑戦） ---
        if not articles:
            for a_tag in all_links:
                href = a_tag['href']
                # /topics/ 以外に記事リンクを特定できるキーワードがないか探す
                if ('/topics/' in href) and len(a_tag.get_text(strip=True)) > 5:
                    full_url = urljoin(base_url, href)
                    title = a_tag.get_text(strip=True)
                    if not any(d['url'] == full_url for d in articles):
                        articles.append({'title': title, 'url': full_url})

        print(f"最終結果: {len(articles)} 件の記事を特定しました。")

        for item in articles[:5]:
            fe = fg.add_entry()
            fe.id(item['url'])
            fe.title(item['title'])
            fe.link(href=item['url'])
            fe.description(get_article_body(item['url']))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')

    except Exception as e:
        print(f"致命的なエラー: {e}")

if __name__ == "__main__":
    create_rss()
