
import os
import re
import json
import html
import feedparser
import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timezone, timedelta
from groq import Groq

# ── PAGE CONFIG
st.set_page_config(page_title="Regulation Radar", page_icon="📡", layout="wide")

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

PRODUCT_DEFINITION = (
    "A consent-based ad personalization API that uses behavioral signals and "
    "first-party data to serve relevant ads across Google surfaces, operating "
    "under user-granted permissions and subject to EU and US privacy frameworks."
)

RSS_FEEDS = {
    "IAPP":       "https://iapp.org/feed/",
    "FPF":        "https://fpf.org/feed/",
    "TechCrunch": "https://techcrunch.com/tag/ai-policy/feed/",
    "EPIC":       "https://epic.org/feed/",
    "EFF":        "https://www.eff.org/rss/updates.xml",
}

STRONG_KEYWORDS = [
    "ai act", "gdpr", "ccpa", "cpra", "virginia cdpa", "texas tdpsa",
    "colorado privacy", "connecticut ai", "ai law", "ai regulation",
    "ai policy", "ai ban", "privacy law", "privacy regulation",
    "data protection law", "ftc", "dark pattern", "data broker",
    "ad targeting", "targeted ad", "behavioral tracking",
    "consent framework", "lawful basis", "first-party data",
    "surveillance pricing", "algorithmic", "enforcement",
]

WEAK_KEYWORDS = [
    "privacy", "consent", "transparency", "tracking",
    "ban", "fine", "penalty", "ruling", "bill", "amendment",
    "legislature", "regulation", "surveillance", "data",
]

BLOCKLIST = [
    "career", "job", "hiring", "workforce", "professional development",
    "women in ai", "interview", "podcast", "event", "conference",
    "webinar", "course", "certification", "award", "fellowship",
]

DAYS_BACK = 14

def clean_summary(text):
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:300]

def is_recent(entry, days=DAYS_BACK):
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            pub = datetime(*t[:6], tzinfo=timezone.utc)
            return pub >= datetime.now(timezone.utc) - timedelta(days=days)
    return True

def matches_keywords(title):
    title_lower = title.lower()
    if any(kw in title_lower for kw in STRONG_KEYWORDS):
        return True
    weak_matches = sum(1 for kw in WEAK_KEYWORDS if kw in title_lower)
    return weak_matches >= 2

def is_blocked(title):
    return any(term in title.lower() for term in BLOCKLIST)

def run_scout():
    seen_titles = set()
    articles = []
    for source, url in RSS_FEEDS.items():
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link  = entry.get("link", "")
            if not title or title in seen_titles:
                continue
            if not is_recent(entry):
                continue
            if is_blocked(title):
                continue
            if not matches_keywords(title):
                continue
            seen_titles.add(title)
            articles.append({
                "source":    source,
                "title":     title,
                "link":      link,
                "published": entry.get("published", "Unknown"),
                "summary":   clean_summary(entry.get("summary", "")),
            })
    return articles

def classify_article(article):
    prompt = f"""
You are a regulatory risk analyst for an ad-tech product.

Product definition:
{PRODUCT_DEFINITION}

Your task: classify the article below and return ONLY a JSON object.
Do NOT summarize the article text. Use the article content only as context for classification.

{{
  "regulation_name": "one of: EU AI Act / GDPR / CCPA / CPRA / Virginia CDPA / Texas TDPSA / Colorado AI Act / Connecticut AI Law / FTC Action / Other",
  "jurisdiction": "one of: EU / US-Federal / US-State / Global",
  "affected_product_area": "one or two of: Ad targeting / Consent UI / Data collection / Model training / First-party data / Transparency obligations / Enforcement",
  "risk_level": "one of: High / Medium / Low",
  "risk_score": "integer 1-10 reflecting impact on the product definition above",
  "enforcement_timeline": "one of: Immediate / 6mo / 1yr / 2yr+ / Unclear",
  "summary": "one sentence YOU write: what this article means for the product defined above"
}}

Article title: {article["title"]}
Article context: {article.get("summary", "Not available")}
Source: {article["source"]}

CRITICAL: Return ONLY the JSON object. No explanation, no markdown, no preamble. Start your response with {{
"""
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
    )
    raw = response.choices[0].message.content.strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
            except:
                parsed = {"error": "parse_failed"}
        else:
            parsed = {"error": "parse_failed"}
    return {**article, **parsed}

def get_quadrant(risk_score, timeline):
    high_impact = risk_score >= 6
    near_term   = timeline in ["Immediate", "6mo", "1yr"]
    if high_impact and near_term:
        return "🔴 Act Now"
    elif high_impact and not near_term:
        return "🟡 Plan Ahead"
    elif not high_impact and near_term:
        return "🟠 Monitor"
    else:
        return "⚪ Park It"

def get_action(quadrant):
    return {
        "🔴 Act Now":    "Escalate to legal + eng. Immediate roadmap impact.",
        "🟡 Plan Ahead": "Add to 6-month planning cycle. Assign owner.",
        "🟠 Monitor":    "Track weekly. No action yet.",
        "⚪ Park It":    "Log and revisit quarterly.",
    }.get(quadrant, "Review manually.")

def run_pipeline():
    with st.spinner("🛰 Scout — fetching regulatory feeds..."):
        articles = run_scout()
    if not articles:
        st.warning("No articles found in the last 14 days.")
        return []
    classified = []
    progress = st.progress(0, text="🔬 Classifier — analyzing articles...")
    for i, a in enumerate(articles):
        result = classify_article(a)
        classified.append(result)
        progress.progress((i + 1) / len(articles),
                          text=f"🔬 Classifying {i+1}/{len(articles)}...")
    ranked = []
    for c in classified:
        if "error" in c:
            continue
        score    = int(c.get("risk_score", 5))
        timeline = c.get("enforcement_timeline", "Unclear")
        quadrant = get_quadrant(score, timeline)
        ranked.append({**c, "risk_score": score,
                       "quadrant": quadrant,
                       "action": get_action(quadrant)})
    ranked.sort(key=lambda x: x["risk_score"], reverse=True)
    return ranked

# ── UI
st.title("📡 Regulation Radar")
st.caption("AI & privacy regulatory signals — scored for ad-tech product impact")

st.sidebar.header("Filters")
filter_jurisdiction = st.sidebar.multiselect("Jurisdiction",
    ["EU", "US-Federal", "US-State", "Global"],
    default=["EU", "US-Federal", "US-State", "Global"])
filter_risk = st.sidebar.multiselect("Risk Level",
    ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
filter_area = st.sidebar.multiselect("Product Area",
    ["Ad targeting", "Consent UI", "Data collection", "Model training",
     "First-party data", "Transparency obligations", "Enforcement"],
    default=["Ad targeting", "Consent UI", "Data collection", "Model training",
             "First-party data", "Transparency obligations", "Enforcement"])
filter_timeline = st.sidebar.multiselect("Enforcement Timeline",
    ["Immediate", "6mo", "1yr", "2yr+", "Unclear"],
    default=["Immediate", "6mo", "1yr", "2yr+", "Unclear"])

if st.button("🔄 Refresh Signals", type="primary"):
    st.session_state["results"] = run_pipeline()
    st.session_state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")

if "results" not in st.session_state:
    st.info("Click **Refresh Signals** to fetch the latest regulatory signals.")
else:
    results = st.session_state["results"]
    st.caption(f"Last updated: {st.session_state.get('last_run', 'Unknown')}")
    if not results:
        st.warning("No results to display.")
    else:
        filtered = [
            r for r in results
            if r.get("jurisdiction")          in filter_jurisdiction
            and r.get("risk_level")           in filter_risk
            and r.get("enforcement_timeline") in filter_timeline
            and any(area in r.get("affected_product_area", "") for area in filter_area)
        ]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Signals",  len(filtered))
        col2.metric("🔴 Act Now",     sum(1 for r in filtered if r["quadrant"] == "🔴 Act Now"))
        col3.metric("🟡 Plan Ahead",  sum(1 for r in filtered if r["quadrant"] == "🟡 Plan Ahead"))
        col4.metric("🟠 Monitor",     sum(1 for r in filtered if r["quadrant"] == "🟠 Monitor"))
        st.divider()

        st.subheader("Risk Matrix")
        df = pd.DataFrame(filtered)
        display_cols = ["quadrant", "risk_score", "regulation_name", "jurisdiction",
                        "affected_product_area", "enforcement_timeline", "title", "summary", "action"]
        df_display = df[[c for c in display_cols if c in df.columns]].copy()
        df_display.columns = ["Quadrant", "Score", "Regulation", "Jurisdiction",
                               "Product Area", "Timeline", "Title", "Summary", "Action"][:len(df_display.columns)]
        st.dataframe(df_display, use_container_width=True, hide_index=True,
            column_config={"Score": st.column_config.ProgressColumn(
                "Score", min_value=0, max_value=10, format="%d")})
        st.divider()

        st.subheader("Impact vs. Timeline")
        timeline_order = {"Immediate": 1, "6mo": 2, "1yr": 3, "2yr+": 4, "Unclear": 5}
        for r in filtered:
            r["timeline_rank"] = timeline_order.get(r["enforcement_timeline"], 5)
        df_chart = pd.DataFrame(filtered)
        if not df_chart.empty:
            color_map = {
                "🔴 Act Now":    "#ef4444",
                "🟡 Plan Ahead": "#f59e0b",
                "🟠 Monitor":    "#f97316",
                "⚪ Park It":    "#9ca3af",
            }
            fig = px.scatter(df_chart, x="timeline_rank", y="risk_score",
                color="quadrant", color_discrete_map=color_map,
                hover_data=["title", "regulation_name", "summary"],
                text="regulation_name", size_max=20)
            fig.update_traces(marker=dict(size=18), textposition="top center")
            fig.update_layout(
                xaxis=dict(tickvals=[1,2,3,4,5],
                           ticktext=["Immediate","6mo","1yr","2yr+","Unclear"],
                           title="Enforcement Timeline →"),
                yaxis=dict(title="Risk Score (Impact) →", range=[0, 11]),
                legend_title="Quadrant", height=450, plot_bgcolor="#f8fafc")
            fig.add_hline(y=6, line_dash="dash", line_color="#cbd5e1")
            fig.add_vline(x=3.5, line_dash="dash", line_color="#cbd5e1")
            st.plotly_chart(fig, use_container_width=True)
        st.divider()

        st.subheader("Signal Details")
        for r in filtered:
            with st.expander(f"{r['quadrant']} — {r['title']}"):
                c1, c2, c3 = st.columns(3)
                c1.markdown(f"**Regulation:** {r.get('regulation_name','N/A')}")
                c2.markdown(f"**Risk Score:** {r.get('risk_score','N/A')}/10")
                c3.markdown(f"**Timeline:** {r.get('enforcement_timeline','N/A')}")
                st.markdown(f"**Product Impact:** {r.get('summary','N/A')}")
                st.markdown(f"**Recommended Action:** {r.get('action','N/A')}")
                st.markdown(f"[Read article →]({r.get('link','#')})")

