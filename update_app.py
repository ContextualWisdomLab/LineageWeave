import re

with open("frontend/src/App.tsx", "r") as f:
    content = f.read()

# Replace hardcoded LineageWeave and BRAND in App component
# I'll inject `const brandName = "LineageWeave"; // TODO: Fetch from admin/tenant config`
# into the App component.

# First, find the beginning of the App component:
# export default function App() {
#   const auth = useAuth();
app_start = "export default function App() {\n  const auth = useAuth();"
new_app_start = "export default function App() {\n  const auth = useAuth();\n  const brandName = \"LineageWeave\"; // TODO: Fetch from admin/tenant config"

content = content.replace(app_start, new_app_start)

# Replace <h1>LineageWeave</h1> with <h1>{brandName}</h1>
content = content.replace("<h1>LineageWeave</h1>", "<h1>{brandName}</h1>")
# Replace <h1 className="app-header-title">LineageWeave</h1> with <h1 className="app-header-title">{brandName}</h1>
content = content.replace('<h1 className="app-header-title">LineageWeave</h1>', '<h1 className="app-header-title">{brandName}</h1>')
# Replace <span className="app-footer-logo">LineageWeave</span> with <span className="app-footer-logo">{brandName}</span>
content = content.replace('<span className="app-footer-logo">LineageWeave</span>', '<span className="app-footer-logo">{brandName}</span>')
# Replace by BRAND with by {brandName}
content = content.replace('by BRAND.', 'by {brandName}.')

with open("frontend/src/App.tsx", "w") as f:
    f.write(content)
