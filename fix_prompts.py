import re
import os

def update_file(path, replacements):
    with open(path, "r") as f:
        content = f.read()
    for old, new in replacements:
        content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)

update_file("lineageweave/post_summary.py", [
    (
        '"major_event_actions": [{"event_type": "string", "actor_name": "string", "actor_company_name": "string"}]',
        '"major_event_actions": [{"event_type": "string", "actor_name": "string", "actor_company_name": "string"}],\n        "projects": ["project1", "project2"],\n        "five_w1h": {"who": "...", "what": "...", "when": "...", "where": "...", "why": "...", "how": "..."}'
    ),
    (
        "For roles_and_responsibilities, list the known tasks",
        "For roles_and_responsibilities, list the known tasks (explicitly specify who requested, who processes, and who approved)"
    )
])

update_file("lineageweave/keyman_extraction.py", [
    (
        "Do not invent roles or affiliations.",
        "Do not invent roles or affiliations. Ensure you extract unnamed specific roles (like 'PMs') and organizational teams (like '설계팀') as keymen if individuals are not named."
    )
])

update_file("lineageweave/organization_name_resolution.py", [
    (
        "Only use information present in the text.",
        "Use information present in the text, but you may use general knowledge to expand well-known abbreviations (e.g. '한전' -> '한국전력') as they will be verified."
    )
])

update_file("lineageweave/image_content.py", [
    (
        'class ImageDescription(BaseModel):',
        'class ImageDescription(BaseModel):\n    ontology_mapping: dict = Field(default_factory=dict)'
    ),
    (
        '"extracted_text": "any text visible in the image"',
        '"extracted_text": "any text visible in the image",\n        "ontology_mapping": {"field": "value"}'
    )
])
