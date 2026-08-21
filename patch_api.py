with open("frontend/src/api.ts", "r") as f:
    content = f.read()

new_api = """
export async function fetchTenantConfig(accessToken: string): Promise<{ brandName: string }> {
  const response = await fetch(`${config.backendBaseUrl}/api/settings`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    throw new Error(`Failed to fetch tenant config: ${response.status}`);
  }
  return response.json();
}

export async function updateTenantConfig(accessToken: string, brandName: string): Promise<{ brandName: string }> {
  const response = await fetch(`${config.backendBaseUrl}/api/settings`, {
    method: "PATCH",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ brandName }),
  });
  if (!response.ok) {
    throw new Error(`Failed to update tenant config: ${response.status}`);
  }
  return response.json();
}
"""

if "fetchTenantConfig" not in content:
    content += new_api
    with open("frontend/src/api.ts", "w") as f:
        f.write(content)
        print("Patched api.ts")
