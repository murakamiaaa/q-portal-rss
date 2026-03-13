import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json

def find_longest_string_recursive(obj):
    """JSONの中から最も長い文字列を執念で探し出す"""
    longest = ""
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, dict):
        for v in obj.values():
            res = find_longest_string_recursive(v)
            if len(res) > len(longest): longest = res
    elif isinstance(obj, list):
        for item in obj:
            res = find_longest_string_recursive(item)
            if len(res) > len(longest): longest = res
    return longest

def get_full_content_from_next_data(html):
    """Next.jsの内部JSONから全文を救出する"""
    soup = BeautifulSoup(html, 'html.parser')
    # Next.js特有のデータタグを探す
    next_data_tag = soup.find('script', id='__NEXT_DATA__')
    
    if next_data_tag:
        try:
            data = json.loads(next_data_tag.string)
            # JSON全体から一番長い文章（＝本文）を探す
            full_text = find_longest_string_recursive(data)
            if len(full_text) > 300: # 300文字以上なら本文とみなす
                # HTMLタグが混じっていれば掃除
                return BeautifulSoup(full_text, 'html.parser').get_text(separator="\n", strip=True)
        except:
            pass
    return None

def create_rss():
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal (Next.js Deep Extract)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("Next.jsの内部ステートを解析して全文を抽出しています")

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"})

    try:
        res = session.post(api_url, json={}, timeout=15)
        articles = res.json().get('data', {}).get('topics', [])
        print(f"--- 解析開始: {len(articles)}件 ---")

        for item in articles[:10]:
            title = item.get('title', '無題')
            url = f"https://q-portal.riken.jp/topics/{item.get('id')}"
            print(f"解析中: {title}")
            
            time.sleep(1)
            detail_res = session.get(url, timeout=10)
            
            # Next.jsの隠し扉をスキャン
            full_text = get_full_content_from_next_data(detail_res.text)
            
            fe = fg.add_entry()
            fe.id(url)
            fe.title(title)
            fe.link(href=url)
            
            if full_text:
                print(f"  -> [成功] {len(full_text)}文字を救出！")
                fe.description(full_text)
            else:
                # それでもダメなら、検索APIの概要を保険にする
                print(f"  -> [失敗] 概要のみ格納")
                fe.description(item.get('description', '全文取得失敗'))

            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("🎉 完了！")
    except Exception as e:
        print(f"エラー: {e}")

if __name__ == "__main__":
    create_rss()