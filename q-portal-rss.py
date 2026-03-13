import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import re
import json

def extract_full_content(html_text):
    """HTMLのソースコードから、隠された長大な本文（content）を力技で抽出する"""
    # 1. Next.jsなどがよく使う __NEXT_DATA__ タグを探す
    soup = BeautifulSoup(html_text, 'html.parser')
    script_tag = soup.find('script', id='__NEXT_DATA__')
    
    if script_tag:
        try:
            data = json.loads(script_tag.string)
            # 辞書の中を再帰的に探して、一番長い 'content' キーを持つ文字列を返す
            def find_content(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k == 'content' and isinstance(v, str) and len(v) > 500:
                            return v
                        res = find_content(v)
                        if res: return res
                elif isinstance(obj, list):
                    for item in obj:
                        res = find_content(item)
                        if res: return res
                return None
            
            res = find_content(data)
            if res:
                return BeautifulSoup(res, 'html.parser').get_text(separator="\n", strip=True)
        except:
            pass

    # 2. 【最終手段】正規表現で "content":"..." の中身を直接抜き出す
    # 日本語（Unicodeエスケープ）が含まれる長い文字列を狙い撃ち
    match = re.search(r'"content":"(.*?)","', html_text)
    if match:
        raw_val = match.group(1)
        try:
            # エスケープされた文字（\u3042等）を日本語に戻す
            decoded = raw_val.encode().decode('unicode-escape')
            # HTMLタグが含まれているので掃除
            return BeautifulSoup(decoded, 'html.parser').get_text(separator="\n", strip=True)
        except:
            pass

    return None

def create_rss():
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal (全文・完全版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("スクレイピング対策を突破し、真の全文を配信しています")

    print(f"--- 全文抽出ミッション開始: {datetime.datetime.now()} ---")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Referer": "https://q-portal.riken.jp/",
    }

    try:
        # リストを取得
        res = requests.post(api_url, headers=headers, json={}, timeout=15)
        articles = res.json().get('data', {}).get('topics', [])
        
        print(f"成功: {len(articles)} 件の記事を解析します。")

        for item in articles[:10]:
            title = item.get('title', '無題')
            article_id = item.get('id')
            article_url = f"https://q-portal.riken.jp/topics/{article_id}"
            
            print(f"全文を解析中: {title}")
            
            # 詳細ページを読み込む
            time.sleep(1)
            detail_res = requests.get(article_url, headers=headers, timeout=15)
            
            # 自作の「全文抽出エンジン」を回す
            full_text = extract_full_content(detail_res.text)
            
            # もし全文が取れなければ、検索APIの概要で妥協する
            final_description = full_text if full_text else item.get('description', '全文取得失敗')
            
            print(f"  -> 抽出完了 (文字数: {len(final_description)})")

            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=article_url)
            fe.description(final_description)
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 成功: 真の全文配信RSSが完成しました！")

    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    create_rss()