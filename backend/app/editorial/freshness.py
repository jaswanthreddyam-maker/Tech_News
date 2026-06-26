import logging
from datetime import datetime, timezone

logger = logging.getLogger("tech_news.editorial.freshness")


def calculate_freshness_multiplier(
    published_at: datetime, decay_model: str = "curved", window_hours: int = 24, now: datetime | None = None
) -> float:
    """
    Calculates freshness multiplier (0.0 to 1.0) based on article age.
    Enforces strict 24-hour expiry (if age >= 24, multiplier is 0.0).
    Supports linear, curved (piecewise linear interpolation), and future extensible models.
    """
    if not published_at:
        return 0.0

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    if published_at.tzinfo is None:
        published_at = published_at.replace(tzinfo=timezone.utc)

    age_hours = (now - published_at).total_seconds() / 3600.0

    if age_hours < 0:
        return 1.0  # Future post protection
    if age_hours >= window_hours:
        return 0.0  # Strict 24h decay window

    if decay_model == "linear":
        return max(0.0, min(1.0, 1.0 - (age_hours / window_hours)))

    elif decay_model == "curved":
        # Curved piecewise linear coordinates
        coords = [(0.0, 1.00), (6.0, 0.95), (12.0, 0.85), (18.0, 0.70), (float(window_hours), 0.00)]
        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            if x1 <= age_hours <= x2:
                # Linearly interpolate within the segment
                return y1 + (y2 - y1) * (age_hours - x1) / (x2 - x1)
        return 0.0

    else:
        # Fallback to linear if unknown decay model specified
        logger.warning(f"Unknown decay model '{decay_model}'. Falling back to linear.")
        return max(0.0, min(1.0, 1.0 - (age_hours / window_hours)))
