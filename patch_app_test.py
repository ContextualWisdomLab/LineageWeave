import re

with open("frontend/src/App.test.tsx", "r") as f:
    content = f.read()

target = """      if (url.endsWith("/api/me/preferences") && method === "PATCH") {"""
replacement = """      if (url.endsWith("/api/settings")) {
        return Promise.resolve(jsonResponse({ brandName: "LineageWeave" }));
      }
      if (url.endsWith("/api/me/preferences") && method === "PATCH") {"""

content = content.replace(target, replacement)

with open("frontend/src/App.test.tsx", "w") as f:
    f.write(content)
