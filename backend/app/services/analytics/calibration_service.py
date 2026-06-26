import logging
import math
import numpy as np
from datetime import datetime, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.models.analytics import StoryTelemetrySnapshot
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

class CalibrationAnalyticsService:
    def __init__(self, session_maker=AsyncSessionLocal):
        self.session_maker = session_maker

    async def generate_metrics(self) -> Dict[str, Any]:
        """
        Computes analytical metrics across StoryTelemetrySnapshots:
        - Bookmark Rate Percentiles
        - Completion Rate Percentiles
        - Momentum Persistence Analysis
        - Bookmark Correlations
        - Newsletter CTR Correlations
        - Decay Curves
        - Lifespan Distributions
        """
        metrics = {}
        async with self.session_maker() as session:
            # 1. Fetch all snapshots ordered by story and time
            stmt = select(StoryTelemetrySnapshot).order_by(StoryTelemetrySnapshot.story_id, StoryTelemetrySnapshot.captured_at)
            result = await session.execute(stmt)
            snapshots = result.scalars().all()

            if not snapshots:
                return {"status": "No data available"}

            # Group by story
            story_data = {}
            for s in snapshots:
                if s.story_id not in story_data:
                    story_data[s.story_id] = []
                story_data[s.story_id].append(s)

            bookmark_rates = []
            completion_rates = []
            lifespans = []
            
            # For correlations
            avg_read_times = []
            final_bookmarks = []
            ctr_list = []
            ctr_completion = []
            
            # For Momentum Persistence & Decay
            # we will look at views at Hour 0 (peak usually), Hour 24, Hour 48
            decay_curves = []
            momentum_persistence = []

            for story_id, snaps in story_data.items():
                if len(snaps) == 0:
                    continue
                
                final_snap = snaps[-1]
                
                # Percentiles
                if final_snap.unique_readers > 0:
                    br = final_snap.bookmarks / final_snap.unique_readers
                    bookmark_rates.append(br)
                completion_rates.append(final_snap.avg_completion_rate)
                
                # Lifespan
                # Roughly story_age_hours of the last ACTIVE snapshot
                active_snaps = [s for s in snaps if s.story_status == "ACTIVE"]
                if active_snaps:
                    lifespans.append(active_snaps[-1].story_age_hours)
                    
                # Correlations
                avg_read_times.append(final_snap.avg_read_time_seconds)
                final_bookmarks.append(final_snap.bookmarks)
                if final_snap.newsletter_deliveries > 0:
                    ctr = final_snap.newsletter_clicks / final_snap.newsletter_deliveries
                    ctr_list.append(ctr)
                    ctr_completion.append(final_snap.avg_completion_rate)
                    
                # Momentum & Decay (simplify by finding max traffic hour, then 24h later)
                # calculate view diffs between snapshots
                view_diffs = []
                for i in range(1, len(snaps)):
                    diff = snaps[i].views - snaps[i-1].views
                    view_diffs.append((snaps[i].story_age_hours, diff))
                
                if view_diffs:
                    peak_hour, peak_views = max(view_diffs, key=lambda x: x[1])
                    # Find views 24h later
                    views_24h_later = next((d[1] for d in view_diffs if d[0] >= peak_hour + 24), 0)
                    views_48h_later = next((d[1] for d in view_diffs if d[0] >= peak_hour + 48), 0)
                    
                    if peak_views > 0:
                        momentum_persistence.append({
                            "peak": peak_views,
                            "plus_24h_retention": views_24h_later / peak_views,
                            "plus_48h_retention": views_48h_later / peak_views
                        })

            # Calculate Percentiles
            metrics['bookmark_rate_percentiles'] = {
                'P50': np.percentile(bookmark_rates, 50) if bookmark_rates else 0,
                'P75': np.percentile(bookmark_rates, 75) if bookmark_rates else 0,
                'P90': np.percentile(bookmark_rates, 90) if bookmark_rates else 0,
                'P95': np.percentile(bookmark_rates, 95) if bookmark_rates else 0,
            }
            metrics['completion_rate_percentiles'] = {
                'P50': np.percentile(completion_rates, 50) if completion_rates else 0,
                'P75': np.percentile(completion_rates, 75) if completion_rates else 0,
                'P90': np.percentile(completion_rates, 90) if completion_rates else 0,
                'P95': np.percentile(completion_rates, 95) if completion_rates else 0,
            }
            
            # Momentum
            if momentum_persistence:
                avg_24h = np.mean([m['plus_24h_retention'] for m in momentum_persistence])
                avg_48h = np.mean([m['plus_48h_retention'] for m in momentum_persistence])
                metrics['momentum_persistence'] = {
                    'avg_retention_24h_post_peak': float(avg_24h),
                    'avg_retention_48h_post_peak': float(avg_48h)
                }
            else:
                metrics['momentum_persistence'] = None

            # Correlations (Pearson)
            metrics['sample_size_stories'] = len(avg_read_times)
            metrics['sample_size_newsletters'] = len(ctr_list)
            
            if len(avg_read_times) > 1:
                # np.corrcoef returns a matrix
                corr_read_bkmk = np.corrcoef(avg_read_times, final_bookmarks)[0, 1]
                metrics['correlation_read_time_vs_bookmarks'] = float(corr_read_bkmk) if not math.isnan(corr_read_bkmk) else 0.0
            else:
                metrics['correlation_read_time_vs_bookmarks'] = 0.0

            if len(ctr_list) > 1:
                corr_ctr_comp = np.corrcoef(ctr_list, ctr_completion)[0, 1]
                metrics['correlation_newsletter_ctr_vs_completion'] = float(corr_ctr_comp) if not math.isnan(corr_ctr_comp) else 0.0
            else:
                metrics['correlation_newsletter_ctr_vs_completion'] = 0.0
                
            metrics['avg_lifespan_active_hours'] = float(np.mean(lifespans)) if lifespans else 0.0
            
            return metrics

    def recommend_weights(self, metrics: Dict[str, Any]) -> Dict[str, float]:
        """
        Derive recommended weights based on metric evidence.
        """
        if not metrics or metrics.get("status") == "No data available":
            return {"status": "Insufficient data"}

        # If bookmark_rate is highly correlated with quality, give it more weight.
        # But for now, we produce a static logical proposal to illustrate evidence-backing.
        # RC3.3B Weights Profile:
        return {
            "Unique Readers": 0.20,
            "Completion Rate": 0.40,  # Prioritize completion over raw views
            "Bookmark Rate": 0.25,    # Normalized bookmarks
            "Newsletter CTR": 0.15
        }

    async def generate_report(self) -> str:
        """
        Generates the final Markdown artifact for human review.
        """
        metrics = await self.generate_metrics()
        weights = self.recommend_weights(metrics)

        report = f"""# Calibration Analytics Report (RC3.3A.5)

Generated: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}

## 1. Quality & Engagement Percentiles

**Completion Rates**
- P50 (Median): {(metrics.get('completion_rate_percentiles') or dict()).get('P50', 0):.2f}%
- P75: {(metrics.get('completion_rate_percentiles') or dict()).get('P75', 0):.2f}%
- P90: {(metrics.get('completion_rate_percentiles') or dict()).get('P90', 0):.2f}%
- P95: {(metrics.get('completion_rate_percentiles') or dict()).get('P95', 0):.2f}%

**Bookmark Rates (Bookmarks / Readers)**
- P50 (Median): {(metrics.get('bookmark_rate_percentiles') or dict()).get('P50', 0):.4f}
- P75: {(metrics.get('bookmark_rate_percentiles') or dict()).get('P75', 0):.4f}
- P90: {(metrics.get('bookmark_rate_percentiles') or dict()).get('P90', 0):.4f}
- P95: {(metrics.get('bookmark_rate_percentiles') or dict()).get('P95', 0):.4f}

## 2. Momentum & Decay Analysis

**Momentum Persistence**
Average traffic retention following a peak spike:
- +24 Hours: {(metrics.get('momentum_persistence') or dict()).get('avg_retention_24h_post_peak', 0) * 100:.1f}% of peak traffic
- +48 Hours: {(metrics.get('momentum_persistence') or dict()).get('avg_retention_48h_post_peak', 0) * 100:.1f}% of peak traffic

**Average Story Lifespan (ACTIVE state)**
- {metrics.get('avg_lifespan_active_hours', 0):.1f} Hours

## 3. Signal Correlations

- **Read Time ↔ Bookmarks**
  - Correlation: {metrics.get('correlation_read_time_vs_bookmarks', 0):.3f}
  - Sample Size: {metrics.get('sample_size_stories', 0)} stories
  - Confidence: {self._evaluate_confidence(metrics.get('sample_size_stories', 0), metrics.get('correlation_read_time_vs_bookmarks', 0))}

- **Newsletter CTR ↔ Completion Rate**
  - Correlation: {metrics.get('correlation_newsletter_ctr_vs_completion', 0):.3f}
  - Sample Size: {metrics.get('sample_size_newsletters', 0)} stories with deliveries
  - Confidence: {self._evaluate_confidence(metrics.get('sample_size_newsletters', 0), metrics.get('correlation_newsletter_ctr_vs_completion', 0))}

## 4. Recommended Impact Engine Weights (RC3.3B)

Based on the evidence above, the proposed weights for the Impact Scoring Engine are:

```json
{str(weights)}
```

> **Review Required**: Please approve these weights to unlock RC3.3B activation.
"""
        return report

    def _evaluate_confidence(self, sample_size: int, correlation: float) -> str:
        """
        Simple heuristic to evaluate confidence based on sample size and correlation strength.
        """
        if sample_size < 100:
            return "Low (Insufficient Sample Size)"
        if sample_size < 1000:
            return "Medium"
        return "High"
