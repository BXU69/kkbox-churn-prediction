# Proposed Retention Experiment

## Status and Objective

Design only; no intervention has been delivered and no experimental outcomes are available.

Test whether a personalized music recommendation and re-engagement reminder reduces churn among previously active subscribers with no recent recorded listening activity.

## Eligibility

At enrollment, require:

- At least four recorded listening days and 20 recorded plays in the preceding seven-day baseline window.
- No listening logs in the most recent seven days.
- Verified logging availability, an active paid subscription expiring within 30 days, and contact eligibility.
- No prior enrollment in this experiment.

Apply eligibility checks before randomization. The historical pool of 5,041 users is not a confirmed eligible population.

## Randomization and Intervention

Randomize users 1:1 using randomly permuted blocks. Persist each assignment and enroll each user once.

Treatment: one personalized recommendation and re-engagement message within 24 hours of assignment.

Control: business-as-usual service without the additional experimental message.

Keep other retention policies equivalent across arms. Record delivery and concurrent campaign exposure.

## Primary Outcome

Freeze the scheduled membership expiration date at enrollment. Define churn as no qualifying paid renewal after assignment and before that date plus 30 days. Early renewals count when they extend valid paid coverage beyond the baseline expiration date.

Validate qualifying renewals using the subscription ledger, including plan changes, cancellations, and reversals. Cancellation alone does not establish churn.

This prospective endpoint is specified separately from the retrospective reconstructed labels. Recalibrate the planning baseline if eligibility or endpoint differences materially change expected control risk.

## Sample Size and Duration

Planning baseline churn: 13.89%.

Target absolute reduction: 2 percentage points, to 11.89%. This is a planning assumption, not an observed treatment effect.

With two-sided alpha 0.05, 80% power, and equal allocation, the normal approximation using Cohen's h requires 4,400 users per arm, or 8,800 total.

Recruit until the fixed sample is reached. Allow up to 60 days of follow-up after the last enrollment, plus data ingestion lag. Daily recruitment scenarios are hypothetical, not forecasts.

## Analysis

Use intention-to-treat: retain users in their assigned arms regardless of message delivery or engagement.

Report treatment-minus-control churn risk difference, its 95% confidence interval, and a two-sided two-proportion test. Negative differences favor treatment.

Check sample-ratio mismatch and data completeness. Report missing outcomes by arm; do not classify them as non-churn or silently exclude them. Include worst-case missing-outcome bounds.

No interim efficacy testing or outcome-driven sample-size changes are planned.

## Secondary Outcomes and Guardrails

Secondary: recorded listening activity during the first seven days after assignment.

Guardrails: notification opt-outs, complaints, and concurrent campaign exposure. Secondary findings are exploratory.

Observed segment differences and predictive lift are not evidence of intervention effectiveness.