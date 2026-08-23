with open("frontend/src/App.tsx", "r") as f:
    content = f.read()

# We have:
#   const [brandName, setBrandName] = useState("LineageWeave");
#   useEffect(() => { ... }, [accessToken]);
#   const auth = useAuth();
#   const [destination, setDestination] = useState<WorkspaceDestination>("board");
#   ...
#   const testOnlyLabPanels = import.meta.env.MODE === "test" && showLabPanels;
#   const accessToken = auth.user?.access_token;

# We need to move the useEffect down after accessToken is defined.

import re

# Remove the bad useEffect
bad_effect_pattern = r"  useEffect\(\(\) => \{\n    if \(accessToken\) \{\n      fetchTenantConfig\(accessToken\).then\(\(config\) => \{\n        if \(config\.brandName\) setBrandName\(config\.brandName\);\n      \}\)\.catch\(console\.error\);\n    \}\n  \}, \[accessToken\]\);\n"
content = re.sub(bad_effect_pattern, "", content)

# Insert it after accessToken is defined
access_token_line = '  const accessToken = auth.user?.access_token;\n'
good_effect = """
  useEffect(() => {
    if (accessToken) {
      fetchTenantConfig(accessToken).then((config) => {
        if (config.brandName) setBrandName(config.brandName);
      }).catch(console.error);
    }
  }, [accessToken]);
"""

content = content.replace(access_token_line, access_token_line + good_effect)

with open("frontend/src/App.tsx", "w") as f:
    f.write(content)
