"""
Layer 2 Sensitivity Analysis Script
===================================
A read-only script that evaluates variations of the classification contract
to calibrate negative penalties and hybrid margins.
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
    return text.lower() if text else ""

def count_matches(text, keywords):
    if not text:
        return 0, []
    sorted_kws = sorted(keywords, key=len, reverse=True)
    count = 0
    matched_words = []
    text_copy = " " + text + " "
    for kw in sorted_kws:
        pattern = r'\b' + re.escape(kw) + r'\b'
        matches = len(re.findall(pattern, text_copy))
        if matches > 0:
            count += matches
            matched_words.append(kw)
            text_copy = re.sub(pattern, ' ', text_copy)
    return count, matched_words

def classify_article(title, content, source_name, config):
    title_norm = normalize_text(title)
    content_norm = normalize_text(content)
    
    scores = {}
    for cat in SPECIALIZED_CATEGORIES:
        d = DICTIONARY[cat]
        t_count, _ = count_matches(title_norm, d["positive"])
        c_count, _ = count_matches(content_norm, d["positive"])
        n_t_count, _ = count_matches(title_norm, d["negative"])
        n_c_count, _ = count_matches(content_norm, d["negative"])
        
        t_score = min(t_count * 3, 9)
        c_score = min(c_count * 1, 5)
        
        # Apply negative penalty logic
        n_score = 0
        if config["neg_penalty"] < 0:
            raw_neg = (n_t_count + n_c_count) * config["neg_penalty"]
            # Protection logic
            if config["protect_strong_pos"] and t_score >= 3:
                raw_neg = 0
            n_score = max(raw_neg, -10)
            
        s_score = 2 if source_name in d["priors"] else 0
        scores[cat] = t_score + c_score + n_score + s_score
        
    sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_cat, best_score = sorted_cats[0]
    second_best_score = sorted_cats[1][1] if len(sorted_cats) > 1 else 0
    margin = best_score - second_best_score
    
    # Gates
    pass_conf = best_score >= config["min_conf"]
    pass_margin = margin >= config["min_margin"]
    pass_evid = (best_score - (2 if source_name in DICTIONARY[best_cat]["priors"] else 0)) > 0
    
    if pass_conf and pass_margin and pass_evid:
        return best_cat
    return "technology"

async def run_sensitivity():
    print("Running Sensitivity Analysis...")
    async with AsyncSessionLocal() as db:
        stmt = select(ArticleReadModel.source).distinct()
        res = await db.execute(stmt)
        sources = res.scalars().all()
        
        articles = []
        for src in sources:
            s_stmt = select(ArticleReadModel).where(ArticleReadModel.source == src).limit(20)
            s_res = await db.execute(s_stmt)
            articles.extend(s_res.scalars().all())

    configs = {
        "Baseline": {"neg_penalty": -5, "protect_strong_pos": False, "min_conf": 4, "min_margin": 2},
        "No Negatives": {"neg_penalty": 0, "protect_strong_pos": False, "min_conf": 4, "min_margin": 2},
        "Reduced Negatives (-2)": {"neg_penalty": -2, "protect_strong_pos": False, "min_conf": 4, "min_margin": 2},
        "Protected Positives": {"neg_penalty": -5, "protect_strong_pos": True, "min_conf": 4, "min_margin": 2},
        "Relaxed Margin (1)": {"neg_penalty": -5, "protect_strong_pos": False, "min_conf": 4, "min_margin": 1},
        "Protected Positives + Margin 1": {"neg_penalty": -5, "protect_strong_pos": True, "min_conf": 4, "min_margin": 1},
        "Protected Positives + Margin 0": {"neg_penalty": -5, "protect_strong_pos": True, "min_conf": 4, "min_margin": 0},
    }

    results = {name: {"fallback": 0, "specialty": 0, "dist": defaultdict(int), "wacom": "", "gemini": ""} for name in configs}

    for art in articles:
        is_wacom = "wacom" in art.title.lower()
        is_gemini = "gemini robotics" in art.title.lower()

        for name, cfg in configs.items():
            cat = classify_article(art.title, art.content, art.source, cfg)
            
            if is_wacom: results[name]["wacom"] = cat
            if is_gemini: results[name]["gemini"] = cat
            
            if cat == "technology":
                results[name]["fallback"] += 1
            else:
                results[name]["specialty"] += 1
                
            results[name]["dist"][cat] += 1

    print("\n" + "="*80)
    print("SENSITIVITY ANALYSIS REPORT")
    print("="*80)
    
    for name, data in results.items():
        print(f"\n[{name}]")
        print(f"Fallback (Technology): {data['fallback']} | Specialty: {data['specialty']}")
        print(f"Wacom Case: {data['wacom']}")
        print(f"Gemini Case: {data['gemini']}")
        # print("Distribution:")
        # for k, v in data["dist"].items():
        #     if k != "technology":
        #         print(f"  {k}: {v}")

if __name__ == "__main__":
    asyncio.run(run_sensitivity())
