import os
import re

versions_dir = "backend/alembic/versions"
migrations = []

for filename in os.listdir(versions_dir):
    if filename.endswith(".py"):
        filepath = os.path.join(versions_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        
        rev_match = re.search(r"revision\s*(?::\s*[\w|\[\]\s]+)?\s*=\s*['\"]([^'\"]+)['\"]", content)
        down_match = re.search(r"down_revision\s*(?::\s*[\w|\[\]\s\\]+)?\s*=\s*['\"]?([^'\"\s\n,)]+)?['\"]?", content)
        
        rev = rev_match.group(1) if rev_match else None
        down = down_match.group(1) if down_match else None
        
        # Strip quotes if present in down_revision
        if down:
            down = down.replace("'", "").replace('"', "")
            if down == "None":
                down = None
        
        migrations.append({"filename": filename, "revision": rev, "down_revision": down})

# Build chain from base (where down_revision is None)
by_down = {m["down_revision"]: m for m in migrations}
curr = None
chain = []
visited = set()

while True:
    next_m = by_down.get(curr)
    if not next_m:
        break
    rev = next_m["revision"]
    if rev in visited:
        print("Cycle detected in migrations!")
        break
    visited.add(rev)
    chain.append(next_m)
    curr = rev

print(f"Total migrations in versions directory: {len(migrations)}")
print(f"Total migrations in chain: {len(chain)}")
print("Migration chain:")
for idx, m in enumerate(chain):
    print(f"{idx+1}: {m['revision']} ({m['filename']}) -> down: {m['down_revision']}")
