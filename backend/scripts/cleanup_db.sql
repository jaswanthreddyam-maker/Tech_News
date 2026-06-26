-- Clean all synthetic data
TRUNCATE TABLE 
    raw_articles, 
    processed_articles, 
    articles,
    tnt_article_topics,
    tnt_article_entities,
    tnt_editorial_decision_logs
CASCADE;

-- Delete test sources
DELETE FROM sources 
WHERE name LIKE 'Test Source%' 
   OR name IN ('Drill Source', 'Synthetic Generator') 
   OR url LIKE '%test.com%' 
   OR url LIKE '%testsource.com%' 
   OR url LIKE '%example.com%';

-- Reset remaining real sources to trigger immediate ingestion
UPDATE sources 
SET failure_count = 0, 
    next_crawl_at = NOW();
