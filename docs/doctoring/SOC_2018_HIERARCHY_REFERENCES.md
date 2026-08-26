# 2018 SOC hierarchy evidence register

ADR 0249 imports only the official four-level 2018 SOC structure. The source
workbook was retrieved from the U.S. Census Bureau's federal mirror of the BLS
artifact and normalized without changing codes, titles, levels, or parents.

| Evidence | Governed use |
|---|---|
| 2018 SOC Structure XLSX, SHA-256 `ade08af40923266f3a854842e888ca3e93c15b26a147c20a2b12a61f4c4f4077` | Authoritative codes, titles, source columns, and hierarchy |
| Normalized CSV, SHA-256 `7de1c9d4da14d8eeb95197974d9dc1989752ebda235dd234b1693f336891f68e` | Deterministic checked-in rendering input |
| 23 / 98 / 459 / 867 source counts | Completeness acceptance, not fitted values |

No title similarity, code-digit rule, employer job architecture, crosswalk,
weight, person trait, or occupation-to-construct score is inferred.

## APA 7 references

U.S. Bureau of Labor Statistics. (2018). *2018 Standard Occupational
Classification system*. U.S. Department of Labor.
https://www.bls.gov/soc/2018/

U.S. Bureau of Labor Statistics. (2018). *Standard Occupational
Classification and coding structure, 2018 SOC*. U.S. Department of Labor.
https://www.bls.gov/soc/2018/soc_2018_class_and_coding_structure.pdf
