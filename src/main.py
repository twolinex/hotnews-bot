# src/main.py  ——  트렌드 키워드 → 최신 기사 → GPT 요약 → 쿠팡 링크 → Stibee 초안
import os, requests, json, datetime
from openai import OpenAI
from pytrends.request import TrendReq

# GitHub Secrets에서 읽어오는 값
NEWS_KEY        = os.getenv("NEWSAPI_KEY")
OPENAI_KEY      = os.getenv("OPENAI_API_KEY")
STIBEE_KEY      = os.getenv("STIBEE_TOKEN")
FORM_URL        = os.getenv("NEWSLETTER_URL", "")
CPCOUPANG_KEY   = os.getenv("CPCOUPANG_KEY")      # 쿠팡 Access Key
CP_TRACK        = os.getenv("CP_TRACK")           # Tracking ID

# 1. 한국 실시간 트렌드 키워드 Top 5
pytrends = TrendReq(hl="ko", tz=540)
keywords = pytrends.trending_searches(pn="south_korea").head(5)[0].tolist()

# 2. 키워드별 최신 기사 1건씩
def get_article(kw):
    url = (
        f"https://newsapi.org/v2/everything?q={kw}"
        f"&pageSize=1&language=ko&sortBy=publishedAt&apiKey={NEWS_KEY}"
    )
    r = requests.get(url, timeout=10).json()
    if r.get("articles"):
        a = r["articles"][0]
        return {"title": a["title"], "url": a["url"], "source": a["source"]["name"], "kw": kw}
    return None

articles = list(filter(None, map(get_article, keywords)))

# 3. 쿠팡 상품 링크(선택)
def get_coupang_link(keyword):
    if not (CPCOUPANG_KEY and CP_TRACK):
        return None
    api = (
        "https://api.coupang.com/v2/providers/affiliate_open_api/"
        "apis/openapi/v1/products/search"
        f"?keyword={keyword}&limit=1"
    )
    headers = {"Authorization": CPCOUPANG_KEY}
    try:
        data = requests.get(api, headers=headers, timeout=10).json().get("data")
        if data:
            return f"{data[0]['productUrl']}&trackingId={CP_TRACK}"
    except Exception:
        pass
    return None

# 4. GPT-4o 요약
client = OpenAI(api_key=OPENAI_KEY)
def gpt_summary(a):
    prompt = (
        f"제목: {a['title']}\n링크: {a['url']}\n"
        "기사를 2줄 한글 요약 + 1줄 인사이트로 출력해 주세요."
    )
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=180,
    )
    return res.choices[0].message.content.strip()

# 5. 블록 만들기
blocks = []
for art in articles:
    txt  = gpt_summary(art)
    link = get_coupang_link(art["kw"])
    block = f"● {art['title']} ({art['source']})\n{txt}"
    if link:
        block += f"\n🔗 [추천 상품 보기]({link})"
    block += f"\n🔗 [기사 보기]({art['url']})"
    blocks.append(block)

body = "\n\n---\n\n".join(blocks)
if FORM_URL:
    body += f"\n\n더 많은 뉴스 구독 👉 {FORM_URL}"
body += "\n\n*본 메일에는 제휴 링크가 포함될 수 있습니다.*"

# 6. Stibee 초안 생성
today   = datetime.date.today().strftime("%y-%m-%d")
payload = {"title": f"[오늘의 화제 뉴스] {today}", "body": body, "type": "regular"}
headers = {"Content-Type": "application/json",
           "Authorization": f"Bearer {STIBEE_KEY}"}
requests.post("https://stibee.com/api/v1/emails",
              headers=headers, data=json.dumps(payload), timeout=15)

print("Done: draft created")
