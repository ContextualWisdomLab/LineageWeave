# Semantic coverage sampling references

This supporting register documents the authorities used by ADR 0242. It does
not make a product decision independently of that ADR.

Australian Bureau of Statistics. (2022). *Basic survey design: Sample design*.
https://www.abs.gov.au/websitedbs/D3310114.nsf/home/Basic%20Survey%20Design%20-%20Sample%20Design

National Institute of Standards and Technology. (n.d.). *Selecting sample
sizes*. In *NIST/SEMATECH e-handbook of statistical methods*.
https://www.itl.nist.gov/div898/handbook/ppc/section3/ppc333.htm

National Institute of Standards and Technology. (n.d.). *Confidence limits*.
In *NIST/SEMATECH e-handbook of statistical methods*.
https://www.itl.nist.gov/div898/handbook/prc/section2/old.prc271.htm

NIST supplies the proportion sample-size relationship and finite-population
correction; ABS defines probability sampling as requiring determinable
selection probabilities and stratified sampling as independent random
selection within strata. ADR 0242 keeps LineageWeave at structural sample
identity and completeness validation and replays the versioned fast-mlsirm
Rust artifact for sample size, finite-population correction, and allocation.
Its current output is sample-level only; corpus inference remains unavailable
until a terminal Rust owner artifact attests the achieved estimand, estimator,
variance, and interval.
