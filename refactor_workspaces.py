import re
with open('backend/app/api/v1/routes/workspaces.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace import
content = content.replace('from app.ai.chat.schemas import OwnerType', 'from app.ai.chat.schemas import OwnerType\nfrom app.api.deps import resolve_owner')

# Remove _resolve_owner function
content = re.sub(r'def _resolve_owner\(request: Request.*?raise HTTPException.*?missing\."\)', '', content, flags=re.DOTALL)

# Replace function arguments and first line
content = re.sub(
    r'request: Request,(\s+)db: AsyncSession = Depends\(get_db\)\n\):\n\s+owner_type, owner_id = _resolve_owner\(request\)', 
    r'owner_info: tuple[OwnerType, str] = Depends(resolve_owner),\1db: AsyncSession = Depends(get_db)\n):\n    owner_type, owner_id = owner_info', 
    content
)

content = re.sub(
    r'request: Request\n\):\n\s+owner_type, owner_id = _resolve_owner\(request\)', 
    r'owner_info: tuple[OwnerType, str] = Depends(resolve_owner)\n):\n    owner_type, owner_id = owner_info', 
    content
)

with open('backend/app/api/v1/routes/workspaces.py', 'w', encoding='utf-8') as f:
    f.write(content)
