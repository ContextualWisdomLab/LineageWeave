import re

with open("backend/app/main.py", "r") as f:
    content = f.read()

# Replace read_tenant_settings
old_read = """@app.get("/api/settings", response_model=dict)
async def read_tenant_settings(
    account: CurrentAccount,
    conn: asyncpg.Connection = Depends(get_db),
):
    row = await conn.fetchrow("SELECT brand_name FROM tenant_settings WHERE id = 1")
    if not row:
        return {"brandName": "LineageWeave"}
    return {"brandName": row["brand_name"]}"""

new_read = """@app.get("/api/settings", response_model=dict)
async def read_tenant_settings(
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
):
    async with pool.acquire() as conn:
        row = await conn.fetchrow("SELECT brand_name FROM tenant_settings WHERE id = 1")
    if not row:
        return {"brandName": "LineageWeave"}
    return {"brandName": row["brand_name"]}"""

# Replace update_tenant_settings
old_update = """@app.patch("/api/settings", response_model=dict)
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
    return {"brandName": brand_name}"""

new_update = """@app.patch("/api/settings", response_model=dict)
async def update_tenant_settings(
    payload: dict,
    account: CurrentAccount = Depends(get_current_account),
    pool: asyncpg.Pool = Depends(get_pool),
):
    # Only admins can change settings
    _require_post_admin(account)
    brand_name = payload.get("brandName", "LineageWeave")
    async with pool.acquire() as conn:
        await conn.execute(
            "INSERT INTO tenant_settings (id, brand_name) VALUES (1, $1) "
            "ON CONFLICT (id) DO UPDATE SET brand_name = $1",
            brand_name
        )
    return {"brandName": brand_name}"""

content = content.replace(old_read, new_read)
content = content.replace(old_update, new_update)

with open("backend/app/main.py", "w") as f:
    f.write(content)
