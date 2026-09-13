"""Temporary bounded patch for Customer Master normalized hint resolution projection."""

from pathlib import Path

path = Path("backend/app/main.py")
text = path.read_text(encoding="utf-8")

old_scoped = '''                select post_id, post_title, created_at,
                       nullif(btrim(source_customer_code), '') as customer_code,
                       nullif(btrim(source_customer_name), '') as customer_name,
                       case when nullif(btrim(source_customer_code), '') is null
                            then nullif(btrim(source_customer_name), '')
                            else null end as customer_name_group
                  from source_post
'''
new_scoped = '''                select source_post.post_id, source_post.post_title, source_post.created_at,
                       nullif(btrim(source_post.source_customer_code), '') as customer_code,
                       nullif(btrim(source_post.source_customer_name), '') as customer_name,
                       case when nullif(btrim(source_post.source_customer_code), '') is null
                            then nullif(btrim(source_post.source_customer_name), '')
                            else null end as customer_name_group,
                       resolution.resolved_corporate_entity_id::text
                           as resolved_corporate_entity_id,
                       resolution.resolved_entity_name,
                       resolution.verification_status_code,
                       resolution.verification_evidence_url
                  from source_post
                  left join source_post_customer_resolution resolution
                    on resolution.post_id = source_post.post_id
                   and resolution.source_customer_code = btrim(source_post.source_customer_code)
'''
if text.count(old_scoped) != 1:
    raise SystemExit(f"expected one scoped customer anchor, found {text.count(old_scoped)}")
text = text.replace(old_scoped, new_scoped, 1)

old_groups = '''                select customer_code, customer_name_group,
                       max(customer_name) as customer_name,
                       count(*) as post_count
                  from ranked
                 group by customer_code, customer_name_group
'''
new_groups = '''                select customer_code, customer_name_group,
                       max(customer_name) as customer_name,
                       count(*) as post_count,
                       count(distinct resolved_corporate_entity_id) as resolution_entity_count,
                       max(resolved_corporate_entity_id) as resolved_corporate_entity_id,
                       max(resolved_entity_name) as resolved_entity_name,
                       max(verification_status_code) as verification_status_code,
                       max(verification_evidence_url) as verification_evidence_url
                  from ranked
                 group by customer_code, customer_name_group
'''
if text.count(old_groups) != 1:
    raise SystemExit(f"expected one customer groups anchor, found {text.count(old_groups)}")
text = text.replace(old_groups, new_groups, 1)

old_select = '''            select top_groups.customer_code, top_groups.customer_name, top_groups.post_count,
                   coalesce(related.related_posts, '[]'::json) as related_posts
'''
new_select = '''            select top_groups.customer_code, top_groups.customer_name, top_groups.post_count,
                   top_groups.resolution_entity_count,
                   case when top_groups.resolution_entity_count = 1
                        then top_groups.resolved_corporate_entity_id end
                       as resolved_corporate_entity_id,
                   case when top_groups.resolution_entity_count = 1
                        then top_groups.resolved_entity_name end as resolved_entity_name,
                   case when top_groups.resolution_entity_count = 1
                        then top_groups.verification_status_code end as verification_status_code,
                   case when top_groups.resolution_entity_count = 1
                        then top_groups.verification_evidence_url end as verification_evidence_url,
                   coalesce(related.related_posts, '[]'::json) as related_posts
'''
if text.count(old_select) != 1:
    raise SystemExit(f"expected one customer select anchor, found {text.count(old_select)}")
text = text.replace(old_select, new_select, 1)

old_projection = '''                "resolution_status": "hint_only",
                "hint_trust": customer_hint_trust(row["customer_name"], row["customer_code"]),
                "provenance": "source_post.source_customer_code/source_post.source_customer_name",
'''
new_projection = '''                "resolution_status": row["verification_status_code"] or "hint_only",
                "resolved_corporate_entity_id": row["resolved_corporate_entity_id"],
                "resolved_entity_name": row["resolved_entity_name"],
                "verification_evidence_url": row["verification_evidence_url"],
                "hint_trust": customer_hint_trust(row["customer_name"], row["customer_code"]),
                "provenance": (
                    "source_post.source_customer_code/source_post.source_customer_name/"
                    "source_post_customer_resolution.resolved_corporate_entity_id"
                ),
'''
if text.count(old_projection) != 1:
    raise SystemExit(f"expected one customer projection anchor, found {text.count(old_projection)}")
text = text.replace(old_projection, new_projection, 1)

path.write_text(text, encoding="utf-8")
