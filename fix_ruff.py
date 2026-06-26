import re

# 1. celery_app.py
with open('backend/celery_app.py', 'r', encoding='utf-8') as f:
    c = f.read()

# Remove the duplicate process_note_embedding_task definition
parts = c.split('@celery_app.task(name="tasks.ai.process_note_embedding_task", bind=True, max_retries=5, default_retry_delay=60)')
if len(parts) == 3:
    c = parts[0] + '@celery_app.task(name="tasks.ai.process_note_embedding_task", bind=True, max_retries=5, default_retry_delay=60)' + parts[1]
    with open('backend/celery_app.py', 'w', encoding='utf-8') as f:
        f.write(c)

# 2. app/ai/service.py
with open('backend/app/ai/service.py', 'r', encoding='utf-8') as f:
    c = f.read()
# B023 Function definition does not bind loop variable
# These variables (circuit_breaker, provider_metadata, enrichment_input_fingerprint, cache_key)
# are used inside an inner def but defined in a loop.
# We can fix this by changing the inner function or passing them as default args.
c = re.sub(
    r'async def _do_enrich\(\):',
    r'async def _do_enrich(circuit_breaker=circuit_breaker, provider_metadata=provider_metadata, enrichment_input_fingerprint=enrichment_input_fingerprint, cache_key=cache_key):',
    c
)
with open('backend/app/ai/service.py', 'w', encoding='utf-8') as f:
    f.write(c)

# 3. app/ai/similarity.py
with open('backend/app/ai/similarity.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('    \n    Returns', '    \n    Returns')
c = re.sub(r' +$', '', c, flags=re.MULTILINE)
with open('backend/app/ai/similarity.py', 'w', encoding='utf-8') as f:
    f.write(c)

# 4. app/backup/storage/__init__.py
with open('backend/app/backup/storage/__init__.py', 'w', encoding='utf-8') as f:
    f.write('from app.backup.storage.base import BaseStorage as BaseStorage\nfrom app.backup.storage.service import get_storage as get_storage\n')

# 5. app/backup/storage/local.py
with open('backend/app/backup/storage/local.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('base_dir: str = None', 'base_dir: str | None = None')
with open('backend/app/backup/storage/local.py', 'w', encoding='utf-8') as f:
    f.write(c)

# 6. scripts/openapi_snapshot.py
with open('backend/scripts/openapi_snapshot.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('   ℹ ', '   i ')
c = re.sub(r' +$', '', c, flags=re.MULTILINE)
with open('backend/scripts/openapi_snapshot.py', 'w', encoding='utf-8') as f:
    f.write(c)

# 7. tests/test_ai_pipeline_integration.py
with open('backend/tests/test_ai_pipeline_integration.py', 'r', encoding='utf-8') as f:
    c = f.read()
c = c.replace('with pytest.raises(Exception):', 'with pytest.raises(ValueError):')
with open('backend/tests/test_ai_pipeline_integration.py', 'w', encoding='utf-8') as f:
    f.write(c)
