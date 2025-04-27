import os, requests, json, datetime
from openai import OpenAI
from pytrends.request import TrendReq

NEWS_KEY   = os.getenv("NEWSAPI_KEY")
OPENAI_KEY = os.getenv("OPENAI_API_KEY")
STIBEE_KEY = os.getenv("STIBEE_TOKEN")
FORM_URL   = os.getenv("NEWSLETTER_URL", "")

pytrends = TrendReq(hl='ko', tz=540)
keywords = pytrends.trending_searches(pn='south_korea').head(5)[0].tolist()

def get_article(kw):
    url = (f"https://newsapi.org/v2/everything?q={kw}"
           f"&pageSize=1&language=ko&sortBy=publishedAt&apiKey={NEWS_KEY}")
    res = requests.get(url, timeout=10).json()
    if res.get("articles"):
        a = res["articles"][0]
        return {"title": a["title"], "url": a["url"], "source": a["source"]["name"]}
    return None

articles = list(filter(None, map(get_article, keywords)))

client = OpenAI(api_key=OPENAI_KEY)
def gpt_summary(a):
    prompt = f"제목: {a['title']}\n링크: {a['url']}\n" \
             f"기사를 2줄 한글 요약 + 1줄 인사이트로 출력해 주세요."
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        max_tokens=180)
    return res.choices[0].message.content.strip()

blocks=[]
for a in articles:
    blocks.append(
        f"● {a['title']} ({a['source']})\n"
        f"{gpt_summary(a)}\n"
        f"🔗 [기사 보기]({a['url']})"
    )

body="\n\n---\n\n".join(blocks)
if FORM_URL:
    body+=f"\n\n더 많은 뉴스 구독 👉 {FORM_URL}"
body+="\n\n*본 메일에는 제휴 링크가 포함될 수 있습니다.*"

payload={
  "title": f"[오늘의 화제 뉴스] {datetime.date.today():%y-%m-%d}",
  "body":  body,
  "type":  "regular"
}
headers={"Content-Type":"application/json",
         "Authorization":f"Bearer {STIBEE_KEY}"}
requests.post("https://stibee.com/api/v1/emails",
              headers=headers, data=json.dumps(payload), timeout=15)
print("Done: draft created")
