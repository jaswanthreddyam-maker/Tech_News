import asyncio

from sqlalchemy import text

from app.core.database import async_engine


async def main():
    async with async_engine.connect() as conn:
        # 1. Fetch recent articles
        res = await conn.execute(
            text(
                "SELECT id, title, source, thumbnail_url, thumbnail_local, thumbnail_status, winner_pass "
                "FROM processed_articles ORDER BY created_at DESC LIMIT 20"
            )
        )
        articles = res.fetchall()

        print(f"{'Article ID':<10} | {'Source':<20} | {'Status':<12} | {'Pass':<10} | {'Title'}")
        print("-" * 100)

        article_ids = []
        for art in articles:
            row = dict(art._mapping)
            safe_title = row["title"].encode("ascii", "replace").decode("ascii")
            print(f"{row['id']:<10} | {row['source'][:20]:<20} | {row['thumbnail_status']!s:<12} | {row['winner_pass']!s:<10} | {safe_title}")
            article_ids.append(row["id"])

        print("\n" + "="*100 + "\n")
        print("AUDIT OF THUMBNAIL DECISION LOGS FOR THESE ARTICLES:")
        print("-" * 100)

        # 2. Fetch decision logs for these articles
        if article_ids:
            # PostgreSQL connection: using ANY(:ids) with a list of integers
            logs_res = await conn.execute(
                text(
                    "SELECT article_id, candidate_url, source, accepted, rejection_reason, width, height, aspect_ratio "
                    "FROM thumbnail_decision_log "
                    "WHERE article_id = ANY(:ids) "
                    "ORDER BY article_id, accepted DESC"
                ),
                {"ids": article_ids}
            )
            logs = logs_res.fetchall()

            current_art_id = None
            for log in logs:
                row = dict(log._mapping)
                if row["article_id"] != current_art_id:
                    current_art_id = row["article_id"]
                    print(f"\n--- Article ID: {current_art_id} ---")

                accepted_str = "ACCEPTED" if row["accepted"] else "REJECTED"
                reason_str = f"Reason: {row['rejection_reason']}" if row["rejection_reason"] else "Success"
                dims_str = f"({row['width']}x{row['height']}, AR: {row['aspect_ratio']:.2f})" if row["width"] and row["aspect_ratio"] else "No Dims"
                print(f"  [{accepted_str}] {row['source']:<20} | {dims_str:<25} | {reason_str:<30} | URL: {row['candidate_url'][:80]}")

if __name__ == "__main__":
    asyncio.run(main())
