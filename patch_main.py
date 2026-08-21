import re

with open("backend/app/main.py", "r") as f:
    content = f.read()

endpoints = """
@app.get("/api/settings", response_model=dict)
async def read_tenant_settings(
    account: CurrentAccount,
    conn: asyncpg.Connection = Depends(get_db),
):
    row = await conn.fetchrow("SELECT brand_name FROM tenant_settings WHERE id = 1")
    if not row:
        return {"brandName": "LineageWeave"}
    return {"brandName": row["brand_name"]}

@app.patch("/api/settings", response_model=dict)
async def update_tenant_settings(
    payload: dict,
    account: CurrentAccount,
    conn: asyncpg.Connection = Depends(get_db),
):
    # Only admins can change settings
    _require_post_admin(account)
    brand_name = payload.get("brandName", "LineageWeave")
    await conn.execute(
        "INSERT INTO tenant_settings (id, brand_name) VALUES (1, $1) "
        "ON CONFLICT (id) DO UPDATE SET brand_name = $1",
        brand_name
    )
    return {"brandName": brand_name}
"""

if "@app.get(\"/api/settings\"" not in content:
    # Insert before the last function or at a logical place
    content = content.replace("async def healthz", endpoints + "\n\nasync def healthz")
    with open("backend/app/main.py", "w") as f:
        f.write(content)
        print("Patched main.py")
else:
    print("Endpoints already exist")
