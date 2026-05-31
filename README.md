# regulation-radar
AI-powered regulatory risk tracker for ad-tech PMs — monitors privacy &amp; AI laws, scores product impact using LLMs

# 📡 Regulation Radar

> A PM tool for tracking AI governance as a product constraint — not a legal checklist.

## What it does

Regulation Radar monitors emerging AI and privacy regulations (EU AI Act, GDPR, CCPA, CPRA, state-level US laws) and scores how they impact a hypothetical consent-based ad personalization product.

Built for product managers who need to think about regulatory risk as a roadmap input, not just a compliance problem.

## How it works

1. **Scout** — ingests regulatory news from 5 RSS feeds (IAPP, FPF, TechCrunch, EPIC, EFF), filters by relevance using keyword matching
2. **Classifier** — sends each article to an LLM (Groq / llama-3.3-70b) with a structured prompt anchored to a specific ad-tech product definition
3. **Analyst** — scores risk 1–10, assigns quadrant (Act Now / Plan Ahead / Monitor / Park It), and outputs a prioritized risk matrix

## Output

- **Risk matrix table** — sortable by score, filterable by jurisdiction, product area, and timeline
- **Impact vs. Timeline 2x2** — visual triage tool for PM prioritization
- **Signal detail cards** — product-anchored summaries with recommended actions

## Reference product

> "A consent-based ad personalization API that uses behavioral signals and first-party data to serve relevant ads across Google surfaces, operating under user-granted permissions and subject to EU and US privacy frameworks."

## Stack

| Layer | Tool |
|---|---|
| LLM | Groq free tier (llama-3.3-70b-versatile) |
| Data sources | RSS feeds (IAPP, FPF, TechCrunch, EPIC, EFF) |
| UI | Streamlit |
| Hosting | Streamlit Community Cloud |

## Why this is different from a ChatGPT search

ChatGPT tells you what a regulation says. Regulation Radar tells you what it means for your product, right now, and what to do about it.

- **Continuous monitoring** — not a one-time snapshot
- **Product-anchored scoring** — every risk score is relative to a specific product definition
- **PM-native output** — quadrant triage, not prose summaries
- **Audit trail** — every signal logged with timestamp and recommended action

## Running locally

```bash
pip install streamlit plotly pandas feedparser groq
GROQ_API_KEY=your-key streamlit run app.py
```

## Built by

Abhishek Singh — MBA Candidate, UC Davis (2026)  
7+ years in B2B SaaS, marketplace, and AI-powered products  
[LinkedIn]([https://linkedin.com/in/your-handle](https://www.linkedin.com/in/aabhishek-singh/)

