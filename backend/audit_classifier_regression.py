"""
Layer 2 Real-World Regression Audit
===================================
A strictly read-only diagnostic script that applies the new multi-signal 
classification mathematical contract to existing database articles.

DOES NOT MODIFY ANY PRODUCTION CODE OR DATABASE RECORDS.
"""

import asyncio
import os
import sys
import re
import csv
from collections import defaultdict

sys.path.insert(0, os.getcwd())

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models.article import ArticleReadModel

# --- 1. Signal Dictionary ---

DICTIONARY = {
    "artificial-intelligence": {
        "positive": ["llm", "transformer", "generative ai", "chatgpt", "neural network", "inference", "machine learning", "training", "gemini", "claude", "gpt", "ai model", "ai agents", "prompt engineering"],
        "negative": ["laptop", "tablet", "smartphone", "review", "funding", "lawsuit", "legislation", "smart home", "cybersecurity"],
        "priors": ["OpenAI Blog", "Anthropic News", "Google DeepMind", "NVIDIA AI Blog", "Google Blog"]
    },
    "cybersecurity": {
        "positive": ["vulnerability", "zero-day", "zero day", "breach", "hacked", "malware", "ransomware", "encryption", "patched", "cve", "exploit", "authentication", "cyber", "cybersecurity", "penetration testing"],
        "negative": ["funding", "startup", "revenue"],
        "priors": []
    },
    "hardware": {
        "positive": ["gpu", "cpu", "processor", "semiconductor", "chip", "silicon", "laptop", "tablet", "smartphone", "review", "gadget", "wacom", "battery", "rtx", "iphone", "macbook", "hardware", "architecture"],
        "negative": ["software", "cloud"],
        "priors": ["NVIDIA AI Blog", "The Verge"]
    },
    "robotics": {
        "positive": ["robot", "robotics", "autonomous", "drone", "self-driving", "humanoid", "waymo", "robotaxi", "boston dynamics"],
        "negative": [],
        "priors": ["Google DeepMind"]
    },
    "science": {
        "positive": ["quantum", "physics", "fusion", "reactor", "space", "nasa", "spacex", "astronomy", "biotech", "medical", "genome", "weather forecasting", "cyclone", "climate"],
        "negative": [],
        "priors": []
    },
    "startups-and-business": {
        "positive": ["funding", "series a", "series b", "venture capital", "valuation", "acquired", "acquisition", "seed stage", "revenue", "q1", "q2", "q3", "q4", "ipo", "enterprise", "startup", "raises"],
        "negative": ["review", "gameplay", "zero-day"],
        "priors": ["TechCrunch"]
    },
    "policy": {
        "positive": ["legislation", "executive order", "regulation", "senate", "congress", "white house", "eu", "lawmaker", "lawsuit", "ruling", "copyright", "antitrust", "mandate", "fcc", "ftc"],
        "negative": [],
        "priors": []
    },
    "technology": {
        "positive": ["browser", "app", "update", "feature", "web", "streaming", "streaming service", "roku", "software"],
        "negative": [],
        "priors": ["The Verge", "TechCrunch", "Ars Technica", "Hacker News"]
    }
}

SPECIALIZED_CATEGORIES = [c for c in DICTIONARY.keys() if c != "technology"]

def normalize_text(text):
    if not text:
        return ""
    # simple lowercase
    return text.lower()

def count_matches(text, keywords):
    """
    Implements longest-match non-overlapping precedence.
    Sort keywords by length (longest first) to match largest phrases first.
    """
    if not text:
        return 0, []
        
    sorted_kws = sorted(keywords, key=len, reverse=True)
    count = 0
    matched_words = []
    
    # We replace matched phrases with spaces to prevent overlapping matches
    # but we only match on word boundaries
    text_copy = " " + text + " "
    
    for kw in sorted_kws:
        pattern = r'\b' + re.escape(kw) + r'\b'
        matches = len(re.findall(pattern, text_copy))
        if matches > 0:
            count += matches
            matched_words.append(kw)
            # Remove matched occurrences
            text_copy = re.sub(pattern, ' ', text_copy)
            
    return count, matched_words

def classify_article(title, content, source_name):
    title_norm = normalize_text(title)
    content_norm = normalize_text(content)
    
    scores = {}
    details = {}
    
    for cat in SPECIALIZED_CATEGORIES:
        d = DICTIONARY[cat]
        
        # Title matches (+3 each, max +9)
        t_count, t_words = count_matches(title_norm, d["positive"])
        t_score = min(t_count * 3, 9)
        
        # Content matches (+1 each, max +5)
        c_count, c_words = count_matches(content_norm, d["positive"])
        c_score = min(c_count * 1, 5)
        
        # Negative matches (-5 each, max -10)
        n_t_count, n_t_words = count_matches(title_norm, d["negative"])
        n_c_count, n_c_words = count_matches(content_norm, d["negative"])
        n_score = max((n_t_count + n_c_count) * -5, -10)
        n_words = n_t_words + n_c_words
        
        # Source prior (+2, max +2)
        s_score = 2 if source_name in d["priors"] else 0
        
        total = t_score + c_score + n_score + s_score
        
        scores[cat] = total
        details[cat] = {
            "title_score": t_score,
            "content_score": c_score,
            "negative_score": n_score,
            "source_score": s_score,
            "title_words": t_words,
            "content_words": c_words,
            "negative_words": n_words,
            "total": total
        }
        
    # Determine winner
    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_cat, best_score = sorted_cats[0]
    second_best_score = sorted_cats[1][1] if len(sorted_cats) > 1 else 0
    margin = best_score - second_best_score
    
    # Check Direct Evidence
    d = details[best_cat]
    has_direct_evidence = (d["title_score"] + d["content_score"]) > 0
    
    # Check Gates
    pass_confidence = best_score >= 4
    pass_margin = margin >= 2
    pass_evidence = has_direct_evidence
    
    final_cat = "technology"
    gate_decision = "Failed "
    
    if pass_confidence and pass_margin and pass_evidence:
        final_cat = best_cat
        gate_decision = "Passed all gates"
    else:
        fails = []
        if not pass_confidence: fails.append("Confidence (<4)")
        if not pass_margin: fails.append("Margin (<2)")
        if not pass_evidence: fails.append("Evidence (0)")
        gate_decision = f"Failed {', '.join(fails)}"

    return {
        "proposed_category": final_cat,
        "best_specialized": best_cat,
        "best_score": best_score,
        "second_score": second_best_score,
        "margin": margin,
        "pass_confidence": pass_confidence,
        "pass_margin": pass_margin,
        "pass_evidence": pass_evidence,
        "gate_decision": gate_decision,
        "details": d,
        "all_scores": scores
    }

async def run_audit():
    print("Starting Layer 2 Read-Only Regression Audit...")
    
    async with AsyncSessionLocal() as db:
        # Sample ~100 articles across sources
        # We will fetch up to 20 per source to ensure diversity
        stmt = select(ArticleReadModel.source).distinct()
        res = await db.execute(stmt)
        sources = res.scalars().all()
        
        articles = []
        for src in sources:
            s_stmt = select(ArticleReadModel).where(ArticleReadModel.source == src).limit(20)
            s_res = await db.execute(s_stmt)
            articles.extend(s_res.scalars().all())
            
        print(f"Sampled {len(articles)} articles across {len(sources)} sources.")
        
        results = []
        stats = {
            "current_dist": defaultdict(int),
            "proposed_dist": defaultdict(int),
            "transition": defaultdict(lambda: defaultdict(int)),
            "source_proposed": defaultdict(lambda: defaultdict(int)),
            "fallback_count": 0,
            "specialized_counts": defaultdict(int),
            "ambiguous_cases": 0,
            "low_confidence_cases": 0,
            "changed_count": 0
        }
        
        for art in articles:
            res = classify_article(art.title, art.content, art.source)
            prop = res["proposed_category"]
            curr = art.category
            
            # Map old category names to new if necessary for comparison
            # Current db uses "Artificial Intelligence", "Cybersecurity", etc.
            curr_slug = curr.lower().replace(" ", "-") if curr else "unknown"
            
            stats["current_dist"][curr_slug] += 1
            stats["proposed_dist"][prop] += 1
            stats["transition"][curr_slug][prop] += 1
            stats["source_proposed"][art.source][prop] += 1
            
            if prop == "technology":
                stats["fallback_count"] += 1
            else:
                stats["specialized_counts"][prop] += 1
                
            if not res["pass_margin"] and res["best_score"] >= 4:
                stats["ambiguous_cases"] += 1
                
            if not res["pass_confidence"]:
                stats["low_confidence_cases"] += 1
                
            if curr_slug != prop:
                stats["changed_count"] += 1

            results.append({
                "id": art.id,
                "source": art.source,
                "title": art.title,
                "current_category": curr_slug,
                "proposed_category": prop,
                "changed": curr_slug != prop,
                **res
            })

        # Save detailed CSV
        csv_path = "regression_audit_results.csv"
        with open(csv_path, "w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                "ID", "Source", "Title", "Current Category", "Proposed Category", "Changed",
                "Best Specialized", "Score", "Margin", "Gate Decision",
                "Title Words", "Content Words", "Negative Words", "Source Score"
            ])
            for r in results:
                d = r["details"]
                writer.writerow([
                    r["id"], r["source"], r["title"], r["current_category"], r["proposed_category"], r["changed"],
                    r["best_specialized"], r["best_score"], r["margin"], r["gate_decision"],
                    ",".join(d["title_words"]), ",".join(d["content_words"]), ",".join(d["negative_words"]), d["source_score"]
                ])
                
        # Print Aggregates
        print("\n" + "="*80)
        print("REGRESSION AUDIT SUMMARY")
        print("="*80)
        print(f"Total Articles Audited: {len(articles)}")
        print(f"Total Categories Changed: {stats['changed_count']} ({(stats['changed_count']/len(articles))*100:.1f}%)")
        print(f"Articles falling back to 'technology': {stats['fallback_count']} ({(stats['fallback_count']/len(articles))*100:.1f}%)")
        print(f"Ambiguous cases (score>=4, margin<2): {stats['ambiguous_cases']}")
        print(f"Low confidence cases (score<4): {stats['low_confidence_cases']}")
        
        print("\n--- Current Category Distribution ---")
        for k, v in sorted(stats["current_dist"].items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")
            
        print("\n--- Proposed Category Distribution ---")
        for k, v in sorted(stats["proposed_dist"].items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")
            
        print("\n--- Source -> Proposed Distribution ---")
        for src, props in stats["source_proposed"].items():
            print(f"  {src}:")
            for k, v in props.items():
                print(f"    - {k}: {v}")
                
        print("\n--- Flagged Changes (Sample of 15) ---")
        changed = [r for r in results if r["changed"]]
        for c in changed[:15]:
            d = c["details"]
            print(f"ID {c['id']} | {c['source']} | Title: {c['title'][:60]}...")
            print(f"   {c['current_category']} -> {c['proposed_category']} | Gate: {c['gate_decision']} (Score: {c['best_score']} Margin: {c['margin']})")
            print(f"   Signals: Title: {d['title_words']} | Body: {d['content_words']} | Neg: {d['negative_words']}")
            print("-" * 50)
            
        print(f"\nDetailed CSV written to {csv_path}")

if __name__ == "__main__":
    asyncio.run(run_audit())
