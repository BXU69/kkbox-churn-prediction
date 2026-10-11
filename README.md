# KKBOX Customer Churn Prediction

An ongoing portfolio project exploring customer churn through SQL, Python, predictive modeling, and retention experiment design.

## Current Progress

Completed data audits, transaction and listening feature engineering, historical label reconstruction, model benchmarking, and initial hyperparameter tuning. Evaluation of the combined features, duration-policy sensitivity checks, retention experiment design, and sequence modeling are planned.

### Initial Findings

- `train.csv`: 992,931 users; 6.39% churn.
- `train_v2.csv`: 970,960 users; 8.99% churn.
- Both label tables have unique user IDs and no missing or invalid labels.
- 11.33% of `train_v2` users have no matching member record.
- Churn is 5.35% among unmatched users and 9.46% among matched users. This is a descriptive association, not a causal finding.
- All labeled users are retained. Unusable ages are treated as missing, and missing gender values are represented as `unknown`.

![Churn by member record availability](reports/figures/churn_by_member_availability.png)

## Transaction Data Audit

Audited both transaction files for date coverage, cross-version overlap, exact duplicate rows in v2, and numeric and binary field validity.

### Findings

- `transactions.csv` contains 21,547,746 rows, with transaction dates from January 2015 through February 2017.
- `transactions_v2.csv` contains 1,431,009 rows: 361,187 historical rows before March 2017 and 1,069,822 March 2017 rows.
- None of the historical v2 rows matches a v1 row across all nine fields.
- Of the historical v2 rows, 9,967 match a v1 user and transaction date; 6,126 match all fields except the membership expiration date.
- No exact duplicate rows were found within v2. Exact duplicates within v1 have not yet been audited.
- Both files contain no missing or unparseable plan durations or amounts, no negative plan durations or amounts, and no invalid auto-renewal or cancellation flags.
- Zero-payment and zero-duration records are retained pending further investigation.
- Expiration dates include values such as January 1, 1970 and October 15, 2036, which require further investigation.

### Processing Decisions

The files will not be concatenated or overwritten based solely on user ID and transaction date. These fields do not uniquely identify a transaction.

Initial feature development will use `transactions.csv` alone. A January 31, 2017 cutoff, taken from the official labeling example, is a provisional configuration. Its alignment with the supplied label files must be verified before model evaluation.

See [the transaction audit notebook](notebooks/02_transaction_audit.ipynb) for the queries and detailed results.

## Transaction Feature Development

Built six candidate transaction features using a 90-day window from December 1, 2016 through February 28, 2017, using `transactions.csv` and the user cohort from `train_v2.csv`.

Features include transaction row count, distinct transaction days, cancellation row count, auto-renewal share, average plan duration, and days since the most recent transaction within the window.

All 970,960 labeled users are retained. Users without window transactions receive zero count features; averages and recency remain missing. A `has_transaction_90d` indicator distinguishes the two groups.

- 943,179 users (97.14%) have window transactions, with a churn rate of 6.79%.
- 27,781 users (2.86%) have no window transactions, with a churn rate of 83.77%.

These are descriptive associations, not causal findings. The cutoff follows a working interpretation of the dataset's March 2017 training update; the exact label-generation parameters have not been independently verified.

User-level feature data is stored locally and excluded from Git. See [the feature notebook](notebooks/03_transaction_features.ipynb), [the SQL query](sql/transaction_features_90d.sql), and [the configuration](reports/transaction_feature_config.json).

## Logistic Regression Baseline

Evaluated three models on the same stratified 80/20 random split of `train_v2`, using transaction features with a February 28, 2017 cutoff. The training set contains 776,768 users and the validation set contains 194,192 users.

Missing-value imputation and standardization are fitted on the training set only.

| Model | Log Loss ↓ | ROC-AUC ↑ | Average Precision ↑ |
|---|---:|---:|---:|
| Constant probability | 0.3024 | 0.5000 | 0.0899 |
| Transaction availability only | 0.2544 | 0.6293 | 0.2869 |
| Logistic regression — all seven features | **0.2008** | **0.8542** | **0.5555** |

The full model reduces Log Loss by approximately 33.6% relative to the constant baseline and 21.1% relative to the availability-only model. This comparison suggests that the additional transaction features provide predictive information beyond transaction availability.

These are initial random-holdout results. Temporal validation, independent test evaluation, and verification of the exact label-generation parameters remain outstanding.

See [the baseline notebook](notebooks/04_baseline_model.ipynb), [model comparison](reports/baseline_model_comparison.csv), and [evaluation configuration](reports/baseline_evaluation_config.json).

## Historical Label Reconstruction

Reconstructed December 2016 churn labels using `transactions.csv`, following the ordering and renewal-gap rules in the provided `WSDMChurnLabeller.scala` example.

- History cutoff: November 30, 2016.
- Candidate expiration dates: December 1–31, 2016.
- Outcome observation ends: January 30, 2017.
- Labeled users: 882,127.
- Churned users: 85,237 (9.66%).
- No observed renewal: 66,442 users.
- Observed renewal with a gap of at least 30 days: 18,795 users.

Six synthetic checks cover no renewal, 29-day and 30-day gaps, cancellation before renewal, early renewal, and same-day subscription and cancellation.

These labels are reconstructed, not official competition labels. Exact parity with the Scala implementation has not been independently verified. Future-derived diagnostic fields are excluded from model inputs.

The historical outcome window ends before the planned February 28, 2017 validation prediction date.

See [the label reconstruction notebook](notebooks/05_historical_labels.ipynb), [candidate selection SQL](sql/historical_candidates.sql), [label SQL](sql/historical_labels.sql), and [configuration](reports/historical_label_config.json).

## Historical Cohort Evaluation

Trained on 882,127 users with reconstructed December 2016 labels and transaction features ending November 30, 2016. Training outcomes are observed through January 30, 2017, before the later prediction cutoff.

Evaluated on 970,960 `train_v2` users with features ending February 28, 2017. Preprocessing and model fitting use historical training data only.

| Model | Log Loss ↓ | ROC-AUC ↑ | Average Precision ↑ |
|---|---:|---:|---:|
| Historical constant probability | 0.3027 | 0.5000 | 0.0899 |
| Historical availability-only model | 0.2551 | 0.6301 | 0.2892 |
| Historical logistic regression | **0.2129** | **0.8296** | **0.5365** |

The full model reduces Log Loss by approximately 29.6% relative to the historical constant baseline.

### Cohort Membership Analysis

| Later-cohort segment | Users | Churn rate | Log Loss | ROC-AUC | Average Precision |
|---|---:|---:|---:|---:|---:|
| Seen in historical training | 736,338 | 4.66% | 0.1681 | 0.7185 | 0.1829 |
| Not seen in historical training | 234,622 | 22.60% | 0.3535 | 0.8730 | 0.7139 |

“Not seen” means absent from the historical training cohort, not necessarily newly registered. Different segment prevalences limit direct comparisons of Log Loss and Average Precision.

### Limitations

This is a retrospective historical cohort evaluation. Reconstructed training labels and official validation labels have different provenance. Exact label parity, validation label-generation parameters, and point-in-time source snapshots have not been independently verified. This is not an untouched independent test.

See [the evaluation notebook](notebooks/06_temporal_validation.ipynb), [model comparison](reports/temporal_model_comparison.csv), [segment results](reports/temporal_segment_results.csv), and [configuration](reports/temporal_evaluation_config.json).

## Untuned Model Comparison

Compared Logistic Regression, XGBoost, and LightGBM using the same seven transaction features, historical training cohort, and later evaluation cohort. No hyperparameter tuning or early stopping was performed.

| Model | Log Loss ↓ | ROC-AUC ↑ | Average Precision ↑ |
|---|---:|---:|---:|
| Logistic Regression | **0.2129** | **0.8296** | **0.5365** |
| XGBoost | 0.2294 | 0.8289 | 0.4906 |
| LightGBM | 0.2299 | 0.8295 | 0.4887 |

Logistic Regression performs best in this initial comparison. Similar ROC-AUC values indicate similar overall ranking performance, while Log Loss and Average Precision distinguish the models more clearly.

These results apply to the current features and untuned configurations. They do not establish that Logistic Regression is universally superior. The limitations of the historical cohort evaluation remain applicable.

See [the comparison notebook](notebooks/07_model_comparison.ipynb), [results](reports/untuned_model_comparison.csv), and [parameters and package versions](reports/untuned_benchmark_config.json).

## Hyperparameter Tuning

Selected parameters using a fixed stratified 80/20 split within the historical training cohort. The search evaluated four Logistic Regression configurations and eight configurations each for XGBoost and LightGBM, minimizing internal validation Log Loss.

Selected models were refitted on all historical training data before later-cohort evaluation. The later cohort was not used in the parameter search or for early stopping.

| Model | Untuned later Log Loss ↓ | Tuned later Log Loss ↓ |
|---|---:|---:|
| Logistic Regression | 0.212926 | 0.212925 |
| XGBoost | 0.229378 | 0.237186 |
| LightGBM | 0.229887 | 0.234045 |

Tuning left Logistic Regression performance essentially unchanged and increased later-cohort Log Loss by approximately 3.40% for XGBoost and 1.81% for LightGBM.

The best configurations on the internal historical holdout did not improve later-period performance. This highlights a limitation of parameter selection within a single historical cohort. Temporal changes and differences in label provenance require further investigation.

Logistic Regression remains the strongest model in the current later-cohort comparison. These results are exploratory; the later cohort has been evaluated repeatedly and is not an untouched independent test.

See [the tuning notebook](notebooks/08_hyperparameter_tuning.ipynb), [before-and-after results](reports/tuning_comparison.csv), and [search configuration](reports/hyperparameter_tuning_config.json).

## Listening Log Audit

Audited 392,106,543 listening records covering January 1, 2015 through February 28, 2017.

No missing user IDs, invalid dates, missing or unparseable song counts, negative song counts, or non-finite listening durations were found.

Listening duration anomalies include:

- 61,493 rows with negative durations.
- 142,993 rows with durations exceeding 86,400 seconds.
- Extreme values near ±9.22 × 10¹⁸ seconds.

The provisional processing policy retains song counts and represents negative or above-24-hour durations as missing, with an anomaly indicator. The upper bound is an analytical assumption requiring sensitivity checks, not a confirmed data-validity rule.

Duplicate user-day checks will be performed on the extracted modeling windows.

The full CSV is scanned with DuckDB rather than loaded into pandas. Raw logs remain local and are excluded from Git.

See [the audit notebook](notebooks/09_user_logs_audit.ipynb), [audit results](reports/user_logs_audit.csv), and [quality policy](reports/user_logs_quality_policy.json).

## Daily Listening Data Preparation

Extracted two 30-day listening windows for the modeling cohorts and saved them as Zstandard-compressed Parquet partitions.

| Cohort | Window | Records | Users with logs | Users without window logs |
|---|---|---:|---:|---:|
| Historical training | Nov 1–30, 2016 | 11,326,275 | 667,477 | 214,650 |
| Later evaluation | Jan 30–Feb 28, 2017 | 12,682,786 | 758,941 | 212,019 |

No duplicate user-day records were found in either extracted window. No deduplication or within-day aggregation was required.

The extracted data occupies approximately 1.04 GiB, compared with the 28.42 GiB raw CSV. User-level data remains local and is excluded from Git.

Song counts, raw listening duration, cleaned duration, and a duration anomaly indicator are retained. The provisional duration threshold still requires sensitivity checks.

Users and days without logs are not yet materialized. Coverage indicators and missing-day handling will be added during feature and sequence construction.

See [the preparation notebook](notebooks/10_daily_listening_data.ipynb), [window summary](reports/listening_window_summary.csv), [duplicate checks](reports/listening_user_day_duplicates.csv), and [configuration](reports/daily_listening_config.json).

## Listening Behavior Features

Aggregated 24,009,061 extracted daily activity records into user-level listening features and joined them to the transaction feature tables.

The combined datasets retain all 882,127 historical training users and 970,960 later evaluation users, with 23 candidate features per user: seven transaction features, fifteen listening features, and one listening-log coverage indicator.

Listening features describe recorded days, playback volume, completed-play ratio, valid listening duration, recency, and changes between the most recent seven days and the preceding seven days.

- Historical training: 667,477 users have window logs; 214,650 do not.
- Later evaluation: 758,941 users have window logs; 212,019 do not.

Recorded-count features are filled with zero for users without logs, with a coverage indicator retained. Duration totals, averages, ratios, and recency remain missing when unavailable. Summed daily unique-song counts are not interpreted as monthly distinct songs.

The transaction window spans 90 days and the listening window spans 30 days, ending at each cohort's feature cutoff. The provisional duration threshold still requires sensitivity checks. Predictive improvements from listening features have not yet been evaluated.

User-level feature tables remain local and are excluded from Git.

See [the feature notebook](notebooks/11_listening_features.ipynb), [aggregation SQL](sql/listening_features_30d.sql), [cohort summary](reports/combined_feature_summary.csv), and [feature configuration](reports/combined_feature_config.json).

## Behavioral Feature Evaluation and Risk Targeting

Compared seven transaction features with 23 combined transaction and listening features using identical historical training and later evaluation cohorts, with fixed model configurations.

| Model | Transaction-only Log Loss ↓ | Combined Log Loss ↓ | Combined ROC-AUC ↑ | Combined AP ↑ |
|---|---:|---:|---:|---:|
| Logistic Regression | 0.212926 | **0.207310** | **0.849893** | **0.550063** |
| XGBoost | 0.229378 | 0.230022 | 0.839235 | 0.489641 |
| LightGBM | 0.229887 | 0.225507 | 0.839498 | 0.494052 |

Listening features reduced Logistic Regression Log Loss by 2.64% and LightGBM Log Loss by 1.91%. XGBoost ranking performance improved, but Log Loss slightly worsened.

### Duration Sensitivity

For Logistic Regression, 12-hour, 24-hour, and 48-hour duration bounds, plus exclusion of all duration-derived features, produced Log Loss values between 0.207280 and 0.207319.

Performance was numerically similar across these checks. The predeclared 24-hour policy is retained; this does not establish that the threshold is operationally correct.

### Highest-Risk 10% of Users

The combined-feature Logistic Regression selected 97,096 users, including 51,950 observed churners:

- Precision@10%: 53.50%.
- Recall@10%: 59.49%.
- Lift@10%: 5.95.

At the same selection budget, listening features identified 1,821 additional churners relative to transaction-only Logistic Regression.

These metrics measure risk concentration, not customers retained or causal intervention effects. Results remain exploratory later-cohort evaluations, with the previously documented label and source-data limitations.

See [the evaluation notebook](notebooks/12_behavior_model_evaluation.ipynb), [feature comparison](reports/behavior_feature_comparison.csv), [duration sensitivity](reports/duration_sensitivity_results.csv), and [targeting results](reports/risk_targeting_results.csv).

## Segment Insights and Retention Hypothesis

Analyzed churn by recorded listening days and recent playback changes using predefined segment rules.

Low log coverage and playback decline did not consistently identify substantially higher-risk groups across cohorts. Missing logs alone are therefore not treated as proof of disengagement.

A more specific exploratory target consists of users with at least four recorded days and 20 recorded plays in the previous seven-day window, followed by no logs in the most recent seven days.

| Cohort | Target churn rate | Stable/increased-play reference | Difference |
|---|---:|---:|---:|
| Historical training | 9.90% | 7.22% | +2.68 pp |
| Later evaluation | 13.89% | 9.32% | +4.57 pp |

The later target segment contains 5,041 users and has approximately 1.49 times the reference group's churn rate. The direction is consistent across cohorts, but this remains an observational comparison with differing label provenance.

### Retention Hypothesis

After verifying logging availability, subscription status, and contact eligibility, test personalized music recommendations or re-engagement reminders for this segment.

The observed churn-rate difference is not an intervention effect. The reference group is not a randomized control group, and no retention experiment has been run.

See [the segment notebook](notebooks/13_retention_segments.ipynb), [segment comparison](reports/retention_segment_comparison.csv), and [rules and hypothesis](reports/retention_segment_config.json).

## Data

Source: [WSDM — KKBOX's Churn Prediction Challenge](https://www.kaggle.com/competitions/kkbox-churn-prediction-challenge/data).

Obtain the data according to the competition rules and extract these files into `data/raw/`:

- `train.csv`
- `train_v2.csv`
- `members_v3.csv`

Raw data is excluded from this repository.

## Run the Data Audit

Use Python 3.11. From the repository root:

```bash
python -m pip install -r requirements.txt
jupyter lab
```

Open `notebooks/01_data_audit.ipynb` and run the cells in order.

## Repository Structure

- `notebooks/`: data audit and analysis
- `sql/`: SQL queries used in the analysis
- `reports/`: aggregate audit results and figures
- `requirements.txt`: Python dependencies

## Next Steps

Verify label periods and feature cutoffs, audit transaction and listening data, and build baseline models before evaluating more complex approaches.
