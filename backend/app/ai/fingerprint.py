import hashlib
import json


def build_enrichment_input_fingerprint(
    *,
    title: str,
    content: str,
    prompt_version: str,
    provider: str,
    model: str,
) -> str:
    payload = {
        "content": content,
        "model": model,
        "prompt_version": prompt_version,
        "provider": provider,
        "title": title,
    }
    canonical_payload = json.dumps(payload, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
