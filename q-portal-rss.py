import requests
from bs4 import BeautifulSoup
from feedgen.feed import FeedGenerator
import datetime
import time
from urllib.parse import urljoin

def get_article_body(url):
    """記事の詳細ページから本文を抽出する"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    try:
        time.sleep(1)
        res = requests.get(url, headers=headers, timeout=15)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 本文が入っていそうな場所を特定
        content = (
            soup.find('div', class_='topics-detail-content') or 
            soup.find('div', class_='p-topics-detail__body') or
            soup.find('article') or 
            soup.find('main')
        )
        
        if content:
            for s in content(['script', 'style']):
                s.decompose()
            return content.get_text(separator="\n", strip=True)
        return "本文の抽出に失敗しました。"
    except Exception as e:
        return f"記事取得エラー: {e}"

def create_rss():
    # 今回はJSONではなく、ブラウザで見ている一覧ページをターゲットにします
    list_url = "https://q-portal.riken.jp/topics?lang=ja"
    base_url = "https://q-portal.riken.jp/"
    
    fg = FeedGenerator()
    fg.id(base_url)
    fg.title("Q-Portal 最新トピックス (全文配信版)")
    fg.link(href=list_url, rel='alternate')
    fg.description("理研 Q-Portal の新着情報をウェブサイトから直接解析して配信中")
    fg.language('ja')

    print(f"--- 実行開始: {datetime.datetime.now()} ---")
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Referer": base_url,
    }

    try:
        print(f"一覧ページを取得中: {list_url}")
        res = requests.get(list_url, headers=headers, timeout=15)
        res.raise_for_status()
        
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 記事へのリンク（/topics/数字）を探す
        # Q-Portalの構造に合わせて、aタグのhrefを全スキャンします
        articles = []
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # 「/topics/」で始まり、かつタイトルっぽいテキストがあるものを抽出
            if '/topics/' in href and a_tag.get_text(strip=True):
                full_url = urljoin(base_url, href)
                title = a_tag.get_text(strip=True)
                
                # 重複除外
                if not any(d['url'] == full_url for d in articles):
                    articles.append({'title': title, 'url': full_url})
        
        print(f"成功: {len(articles)} 件の記事リンクを見つけました。")

        # 最新5件を処理
        for item in articles[:5]:
            print(f"解析中: {item['title']}")
            
            fe = fg.add_entry()
            fe.id(item['url'])
            fe.title(item['title'])
            fe.link(href=item['url'])
            
            # 本文を詳細ページから取得
            body = get_article_body(item['url'])
            fe.description(body)
            fe.pubDate(datetime.datetime.now(datetime.timezone.utc))

        fg.rss_file('feed.xml')
        print("成功: feed.xml を生成しました。")

    except Exception as e:
        print(f"致命的なエラー: {e}")

if __name__ == "__main__":
    create_rss()
