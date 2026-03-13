import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json
import re

def clean_and_extract_japanese(raw_str):
    """Unicodeエスケープを解除し、日本語として読める状態にする"""
    try:
        # \uXXXX 形式を日本語に変換
        decoded = raw_str.encode().decode('unicode-escape')
        # HTMLタグが混じっている場合は掃除
        return BeautifulSoup(decoded, 'html.parser').get_text(separator="\n", strip=True)
    except:
        return raw_str

def get_article_body(session, url):
    """HTML内の全スクリプトタグをスキャンして本文を特定する"""
    try:
        time.sleep(1)
        res = session.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        candidates = []

        # 全 script タグをスキャン
        for script in soup.find_all('script'):
            content = script.string
            if content and ('理研' in content or '量子' in content):
                # 正規表現で "content":"..." や "body":"..." の中身を強引に抜く
                # 前後のダブルクォートに挟まれた100文字以上の日本語っぽい部分を探す
                found = re.findall(r'"([^"]{200,})"', content)
                for f in found:
                    candidates.append(clean_and_extract_japanese(f))

        if candidates:
            # 見つかった候補の中で、最も「本文らしい」長いものを採用
            best_match = max(candidates, key=len)
            if len(best_match) > 100:
                return best_match

        # 予備：従来のタグベース
        body_tag = soup.find('div', class_='topics-detail-content') or soup.find('article')
        if body_tag:
            return body_tag.get_text(separator="\n", strip=True)

        return "本文の特定に失敗しました。サイト側で強力なスクレイピング対策が施されている可能性があります。"
    except Exception as e:
        return f"解析エラー: {e}"

def create_rss():
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 全文配信 (Forensic Edition)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("スクリプトタグ全走査により、特殊構造のサイトから本文を抽出中")
    fg.language('ja')

    print(f"--- 最終捜索開始: {datetime.datetime.now()} ---")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://q-portal.riken.jp",
        "Referer": "https://q-portal.riken.jp/",
    })

    try:
        # APIからリストを取得
        res = session.post(api_url, json={}, timeout=15)
        articles = res.json().get('data', {}).get('topics', [])
        print(f"成功: {len(articles)} 件の記事を解析します。")

        for item in articles[:10]:
            title = item.get('title', '無題')
            article_url = f"https://q-portal.riken.jp/topics/{item.get('id')}"
            print(f"深層解析中: {title}")
            
            fe = fg.add_entry()
            fe.id(article_url)
            fe.title(title)
            fe.link(href=article_url)
            fe.description(get_article_body(session, article_url))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("成功: feed.xml を更新しました。")

    except Exception as e:
        print(f"致命的エラー: {e}")

if __name__ == "__main__":
    create_rss()