import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
import json
import re

def get_article_body(session, url):
    """詳細ページの奥深くに隠されたJSONから、執念で本文を引っこ抜く"""
    try:
        time.sleep(1) # サーバーへの礼儀
        res = session.get(url, timeout=15)
        res.raise_for_status()
        
        # 1. Next.js等の埋め込みJSON (__NEXT_DATA__) を徹底捜索
        soup = BeautifulSoup(res.text, 'html.parser')
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        
        if next_data_script:
            data = json.loads(next_data_script.string)
            # 可能性のある階層を順番に掘り進む
            try:
                # パターンA: pageProps -> topic -> content
                topic_data = data.get('props', {}).get('pageProps', {}).get('topic', {})
                content_html = topic_data.get('content')
                
                # パターンB (階層が違う場合): pageProps -> data -> content
                if not content_html:
                    content_html = data.get('props', {}).get('pageProps', {}).get('data', {}).get('content')

                if content_html:
                    # HTMLタグを掃除して純粋なテキストにする
                    return BeautifulSoup(content_html, 'html.parser').get_text(separator="\n", strip=True)
            except Exception as e:
                print(f"DEBUG: JSON解析中にスキップ: {e}")

        # 2. 【予備】HTMLの全テキストから、それっぽい長文ブロックを強引に探す
        # （もしJSONが見つからない場合、100文字以上のテキストを持つタグを探す）
        for tag in soup.find_all(['div', 'section', 'article']):
            text = tag.get_text(strip=True)
            if len(text) > 200 and "理研" in text: # 200文字以上で「理研」を含むなら本文の可能性大
                return tag.get_text(separator="\n", strip=True)

        return "本文の抽出に失敗しました（構造が特殊です）。"

    except Exception as e:
        return f"取得エラー: {e}"

def create_rss():
    # 碧さんが見つけた黄金のAPI
    api_url = "https://q-portal-editor.riken.jp/api/v1/ja/search/topics?year=&target2=&fields=&category=&info_type=3"
    
    fg = FeedGenerator()
    fg.id("https://q-portal.riken.jp/")
    fg.title("Q-Portal 最新トピックス (全文完全版)")
    fg.link(href="https://q-portal.riken.jp/topics/", rel='alternate')
    fg.description("量子コンピュータの最新ニュースを全文配信中")
    fg.language('ja')

    print(f"--- 最終ミッション開始: {datetime.datetime.now()} ---")
    
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Origin": "https://q-portal.riken.jp",
        "Referer": "https://q-portal.riken.jp/",
    })

    try:
        # 1. APIから記事一覧をPOSTで取得
        res = session.post(api_url, json={}, timeout=15)
        res.raise_for_status()
        root_data = res.json()
        articles = root_data.get('data', {}).get('topics', [])

        print(f"成功: {len(articles)} 件のデータを取得。詳細解析に移行します。")

        # 最新10件の全文を丁寧に取得
        for item in articles[:10]:
            title = item.get('title', '無題')
            article_id = item.get('id')
            article_url = f"https://q-portal.riken.jp/topics/{article_id}"
            
            print(f"全文を抽出中: {title}")
            
            fe = fg.add_entry()
            fe.id(str(article_id))
            fe.title(title)
            fe.link(href=article_url)
            
            # 本文の抽出（強化版関数を使用）
            fe.description(get_article_body(session, article_url))
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        # 2. ファイルに保存
        fg.rss_file('feed.xml')
        print("🎉 feed.xml の最終更新が完了しました！")

    except Exception as e:
        print(f"致命的なエラー: {e}")

if __name__ == "__main__":
    create_rss()