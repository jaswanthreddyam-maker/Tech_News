# Thumbnail Certification Report

## Certification Badge

| Grade | Articles | Fallback Rate | Duplicate Rate | Avg Candidates | Avg Time | Status |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **B** | 45 | 4.4% | 0.0% | 4.4 | 5.77s | **FAIL** |

## Version Metadata
- **Date**: 2026-06-24 10:04:23
- **Git Commit**: `967c495`
- **Python**: 3.13.12
- **OS**: Windows 11
- **Run Type**: snapshot

## Trend vs Previous Run

| Metric | Trend |
|---|---|
| fallback_rate | — |
| avg_candidates | → No change |
| avg_html_kb | → No change |
| duplicate_rate | — |
| avg_time | ↑ 1.3 → 5.8 ⚠️ Regressed |

## Quality Gates

| Metric | Value | Threshold | Result |
|---|---|---|---|
| Fallback Rate | 4.4% | < 3.0% | ❌ |
| Avg Candidates | 4.4 | > 3 | ✅ |
| Duplicate Rate | 0.0% | < 2.0% | ✅ |
| Avg HTML | 565.4 KB | > 39 KB | ✅ |
| Download Failures | 4.4% | < 2.0% | ❌ |
| Avg Processing Time | 5.77s | < 2.0s | ❌ |

## Domain Leaderboard

| # | Domain | Articles | Fallback % | Avg HTML | Avg Cands | Avg Time |
|:---:|---|:---:|:---:|:---:|:---:|:---:|
| 1 | blogs.nvidia.com | 3 | 0.0% | 114.5k | 2.3 | 22.64s |
| 2 | nvidianews.nvidia.com | 2 | 0.0% | 75.3k | 1.0 | 5.15s |
| 3 | techcrunch.com | 10 | 0.0% | 227.1k | 3.5 | 5.00s |
| 4 | theverge.com | 10 | 0.0% | 552.8k | 3.4 | 3.19s |
| 5 | tomshardware.com | 10 | 0.0% | 1555.4k | 10.8 | 3.86s |
| 6 | arstechnica.com | 10 | 20.0% | 159.3k | 1.0 | 6.11s |

## Winner Distribution

- **og:image**: 95.6% (43)
- **fallback**: 4.4% (2)

## Failure Reasons

- **network_timeout**: 2

## Failure Samples

### `https://arstechnica.com/space/2026/06/tests-suggest-russian-satellites-can-jam-gps-on-a-continental-scale/`
- **Reason**: network_timeout
- **HTML Length**: 157,244 bytes
- **Candidates Found**: 1
- **Rejections**:
  - `og:image` → network_timeout (https://cdn.arstechnica.net/wp-content/uploads/2026/06/Cloud-free_Europe-2560x14…)

### `https://arstechnica.com/tech-policy/2026/06/meta-alleges-nso-violated-spyware-injunction-with-new-whatsapp-attacks/`
- **Reason**: network_timeout
- **HTML Length**: 148,751 bytes
- **Candidates Found**: 1
- **Rejections**:
  - `og:image` → network_timeout (https://cdn.arstechnica.net/wp-content/uploads/2026/06/whatsapp-icon-1152x648.jp…)
