"""
Layer 2 Final Calibration: Hybrid Cases
=======================================
Read-only script to test evidence-based tie-breakers and protected positives
against synthetic hybrid cases and real data.
"""

import asyncio
import os
import sys
import re
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
    details = {}
    for cat in SPECIALIZED_CATEGORIES:
        d = DICTIONARY[cat]
        
        pos_kws = d["positive"]
        # Apply +4 niche if config asks
        niche_boost = config.get("niche_boost", False)
        t_mult = 4 if niche_boost and cat not in ["artificial-intelligence", "startups-and-business"] else 3
        
        t_count, _ = count_matches(title_norm, pos_kws)
        c_count, _ = count_matches(content_norm, pos_kws)
        n_t_count, _ = count_matches(title_norm, d["negative"])
        n_c_count, _ = count_matches(content_norm, d["negative"])
        
        t_score = min(t_count * t_mult, 9)
        c_score = min(c_count * 1, 5)
        
        raw_neg = (n_t_count + n_c_count) * -5
        
        # Protected Positives Logic
        if config.get("protect_positives"):
            # Only protect if title has strong positive evidence AND title has NO negative evidence
            if t_score >= 3 and n_t_count == 0:
                raw_neg = 0
                
        n_score = max(raw_neg, -10)
        s_score = 2 if source_name in d["priors"] else 0
        
        total = t_score + c_score + n_score + s_score
        scores[cat] = total
        details[cat] = {
            "t": t_score, "c": c_score, "n": n_score, "s": s_score
        }
        
    # Tie-breaking logic
    def sort_key(item):
        cat, score = item
        d = details[cat]
        # Primary: Total Score
        key = [score]
        
        if config.get("tie_breaker") == "evidence_density":
            # 1. Higher Title Evidence
            key.append(d["t"])
            # 2. Higher Content Evidence
            key.append(d["c"])
            # 3. Higher overall Direct Evidence (t+c)
            key.append(d["t"] + d["c"])
            # 4. Less Negative Penalty (n is negative, so higher is better)
            key.append(d["n"])
        elif config.get("tie_breaker") == "hierarchy":
            hierarchy = {"cybersecurity":7, "policy":6, "science":5, "robotics":4, "hardware":3, "startups-and-business":2, "artificial-intelligence":1}
            key.append(hierarchy.get(cat, 0))
            
        return tuple(key)

    sorted_cats = sorted(scores.items(), key=sort_key, reverse=True)
    best_cat, best_score = sorted_cats[0]
    second_best_score = sorted_cats[1][1] if len(sorted_cats) > 1 else 0
    margin = best_score - second_best_score
    
    pass_conf = best_score >= 4
    pass_margin = margin >= config.get("min_margin", 1)
    pass_evid = (details[best_cat]["t"] + details[best_cat]["c"]) > 0
    
    if pass_conf and pass_margin and pass_evid:
        return best_cat, scores, details
    return "technology", scores, details


SYNTHETIC_CASES = [
    ("AI + Robotics", "Google DeepMind", "Gemini AI model brings whole body intelligence to robotics", "New autonomous drone robot operates with LLM inference."),
    ("AI + Cybersecurity", "OpenAI Blog", "Cybersecurity zero-day vulnerability patched in new generative AI training run", "The exploit was hacked using prompt engineering."),
    ("AI + Hardware", "NVIDIA AI Blog", "New GPU chip accelerates LLM and neural network inference", "The semiconductor architecture improves AI model speed."),
    ("AI + Science", "Google Blog", "Quantum reactor uses machine learning for fusion climate physics", "A new AI model breakthrough in weather forecasting."),
    ("AI + Policy", "The Verge", "EU lawmakers draft new legislation on generative AI regulation", "The Senate antitrust lawsuit impacts ChatGPT."),
    ("AI + Business", "TechCrunch", "AI startup raises $50M Series A funding for new generative AI model", "Venture capital acquisition valuation reaches $1B."),
    ("Robotics + Business", "TechCrunch", "Boston Dynamics robotics startup raises Series B venture capital", "The humanoid robot company acquired seed stage funding."),
    ("Hardware + Business", "The Verge", "Semiconductor chip manufacturer raises Series A for new GPU factory", "The hardware startup valuation hits $5B funding."),
    ("Cybersecurity + Policy", "Ars Technica", "Senate legislation mandates new cybersecurity encryption standards", "The EU lawsuit over ransomware zero-day exploits."),
    ("Science + AI", "Anthropic News", "Climate genome biotech uses LLM inference for space physics", "The neural network helps astronomy fusion.")
]


async def run_hybrid_calibration():
    print("="*80)
    print("HYBRID CASE CALIBRATION")
    print("="*80)
    
    configs = {
        "Baseline": {"protect_positives": True, "min_margin": 1, "niche_boost": False, "tie_breaker": None},
        "Niche +4": {"protect_positives": True, "min_margin": 1, "niche_boost": True, "tie_breaker": None},
        "Hierarchy": {"protect_positives": True, "min_margin": 1, "niche_boost": False, "tie_breaker": "hierarchy"},
        "Evidence-Density": {"protect_positives": True, "min_margin": 1, "niche_boost": False, "tie_breaker": "evidence_density"}
    }
    
    for case_name, source, title, content in SYNTHETIC_CASES:
        print(f"\n--- {case_name} ---")
        print(f"Title: {title}")
        
        for cfg_name, cfg in configs.items():
            best_cat, scores, details = classify_article(title, content, source, cfg)
            
            # Sort raw scores
            sorted_raw = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            top1_cat, top1_score = sorted_raw[0]
            top2_cat, top2_score = sorted_raw[1]
            margin = top1_score - top2_score
            
            # Determine reason
            reason = ""
            if best_cat == "technology":
                if margin < cfg["min_margin"]:
                    reason = f"Tie/Margin Failed ({top1_cat}={top1_score} vs {top2_cat}={top2_score})"
                elif top1_score < 4:
                    reason = f"Confidence Failed (Max {top1_score})"
                else:
                    reason = "Evidence Failed"
            else:
                reason = f"Passed gates. Margin={margin}"
                if margin == 0 and cfg.get("tie_breaker"):
                    reason += f" -> Tie broken by {cfg_name} (T={details[best_cat]['t']} C={details[best_cat]['c']})"
            
            print(f"[{cfg_name:18}] -> {best_cat.ljust(25)} | {reason}")


if __name__ == "__main__":
    asyncio.run(run_hybrid_calibration())
