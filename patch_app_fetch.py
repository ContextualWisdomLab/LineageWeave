with open("frontend/src/App.tsx", "r") as f:
    content = f.read()

# Add imports for fetchTenantConfig
content = content.replace(
    '} from "./api";',
    '  fetchTenantConfig,\n} from "./api";'
)

# Replace standard state with fetch hook inside App
old_state = '  const [brandName, setBrandName] = useState("LineageWeave");'
new_state = """  const [brandName, setBrandName] = useState("LineageWeave");
  useEffect(() => {
    if (accessToken) {
      fetchTenantConfig(accessToken).then((config) => {
        if (config.brandName) setBrandName(config.brandName);
      }).catch(console.error);
    }
  }, [accessToken]);"""

content = content.replace(old_state, new_state)

with open("frontend/src/App.tsx", "w") as f:
    f.write(content)
