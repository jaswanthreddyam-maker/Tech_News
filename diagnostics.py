import json
from collections import Counter

def format_report():
    with open('thumbnail_diagnostics.json', 'r', encoding='utf-16') as f:
        data = json.load(f)
    
    articles = data.get('articles', [])
    logs = data.get('logs', [])
        
    print("THUMBNAIL PIPELINE DIAGNOSTIC MODE\n")
    print("="*50)
    print("MOST RECENT 20 PROCESSED ARTICLES")
    print("="*50)
    
    fallback_count = 0
    fallback_reasons = Counter()
    rejection_reasons = Counter()
    total_rejections = 0
    
    source_stats = {
        'nvidia': {'total': 0, 'no_cand': 0, 'rejected': 0, 'dup_lost': 0, 'wrong_fallback': 0},
        'techcrunch': {'total': 0, 'no_cand': 0, 'rejected': 0, 'dup_lost': 0, 'wrong_fallback': 0},
        'theverge': {'total': 0, 'no_cand': 0, 'rejected': 0, 'dup_lost': 0, 'wrong_fallback': 0}
    }
    
    for a in articles:
        print(f"\nTitle: {a.get('title')}")
        src_url = a.get('source_url') or ""
        print(f"Source URL: {src_url}")
        cand_count = a.get('candidate_count') or 0
        wpass = a.get('winner_pass') or ""
        print(f"Candidates: {cand_count}")
        print(f"Source: {a.get('thumbnail_source')}")
        print(f"Winner Pass: {wpass}")
        print(f"Selected Score: {a.get('selected_score')}")
        print(f"Thumbnail URL: {a.get('thumbnail_url')}")
        
        is_fallback = (wpass == 'fallback' or a.get('thumbnail_source') == 'fallback')
        if is_fallback:
            fallback_count += 1
            if cand_count == 0:
                fallback_reasons['Zero candidates found'] += 1
            else:
                fallback_reasons['All candidates failed validation'] += 1
                
        # Domain tracking
        domain_key = None
        if 'nvidia.com' in src_url.lower(): domain_key = 'nvidia'
        elif 'techcrunch.com' in src_url.lower(): domain_key = 'techcrunch'
        elif 'theverge.com' in src_url.lower(): domain_key = 'theverge'
        
        if domain_key:
            source_stats[domain_key]['total'] += 1
            if cand_count == 0:
                source_stats[domain_key]['no_cand'] += 1
            elif is_fallback:
                source_stats[domain_key]['rejected'] += 1
        
        # Logs for this article
        art_logs = [l for l in logs if l.get('article_id') == a.get('id')]
        if art_logs:
            print("  Candidates Evaluated:")
            for l in art_logs:
                print(f"  - URL: {l.get('candidate_url')}")
                print(f"    Source: {l.get('source')}")
                print(f"    Dimensions: {l.get('width')}x{l.get('height')} (AR: {l.get('aspect_ratio')})")
                print(f"    Accepted: {l.get('accepted')}")
                if not l.get('accepted'):
                    rr = l.get('rejection_reason')
                    print(f"    Rejection Reason: {rr}")
                    rejection_reasons[rr] += 1
                    total_rejections += 1
                    
                    if domain_key and is_fallback and cand_count > 0 and 'duplicate' in rr:
                        source_stats[domain_key]['dup_lost'] += 1
                print()

    print("\n" + "="*50)
    print("DIAGNOSTIC SUMMARY")
    print("="*50)
    print(f"\n1. Articles reaching fallback: {fallback_count} / {len(articles)}")
    
    print("\n2. Why they reached fallback:")
    for k, v in fallback_reasons.items():
        print(f"  - {k}: {v}")
        
    print("\n3. Top rejection reasons:")
    for k, v in rejection_reasons.most_common():
        print(f"  - {k}: {v}")
        
    print("\n4. Percentage rejected by reason:")
    if total_rejections > 0:
        for k, v in rejection_reasons.items():
            print(f"  - {k}: {(v/total_rejections)*100:.1f}%")
    else:
        print("  - No rejections logged.")
        
    print("\n5. Source-Specific Inspection:")
    for dom, stats in source_stats.items():
        print(f"\n  Domain: {dom.upper()} (Total: {stats['total']})")
        print(f"  - A) No candidates extracted: {stats['no_cand']}")
        print(f"  - B) Candidates extracted but rejected: {stats['rejected']}")
        print(f"  - C) Candidates lost to duplicate checks: {stats['dup_lost']}")
        print(f"  - D) Incorrectly selected fallback (bugs): {stats['wrong_fallback']}")

if __name__ == '__main__':
    format_report()
