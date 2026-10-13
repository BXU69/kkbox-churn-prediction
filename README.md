# KKBOX Customer Churn Prediction

A portfolio project combining large-scale data auditing, SQL feature engineering, churn modeling, retention experiment design, a PyTorch GRU benchmark, and a sampled BigQuery-to-Tableau analytics workflow.

[Explore the interactive Tableau dashboard](https://public.tableau.com/app/profile/becca.xu/viz/KKBoxChurnOverviewBigQueryTableau/KKBoxChurnOverview)

## Highlights

- Audited **21.5M original transaction records** and **392.1M listening activity records** using SQL and Python.
- Extracted **24.0M daily activity records** and built **23 transaction and listening features**.
- Compared Logistic Regression, XGBoost, LightGBM, and a GRU using historical training data and a later evaluation cohort.
- Designed a randomized retention experiment with power analysis; no experiment was run.
- Migrated seven transaction features to BigQuery for a deterministic **10,000-user sample**, verified parity with DuckDB, and queried the cloud results with Python.
- Published an interactive Tableau Public dashboard showing observed churn by transaction recency and auto-renewal history, with linked filtering and user counts.

## BigQuery and Tableau

The cloud extension uses **10,000 users and 27,094 transaction records** from December 1, 2016 through February 28, 2017. It supplements the larger local modeling workflow; listening features and model training were not migrated to BigQuery.

- **SQL migration:** All seven transaction features and the label matched DuckDB for every sampled user, including null patterns. Counts matched exactly; averages matched within a numerical tolerance of 1e-10.
- **Partitioning:** Historical date partitions immediately expired under the sandbox's 60-day partition retention. The working table uses an integer month index for range partitioning, retains the original dates, and clusters by user ID.
- **Scan comparison:** Equivalent January aggregate queries processed **635.02 KB** on the raw table and **218.32 KB** on the partitioned table, approximately **65.6% less data**. Single-run durations were 190 ms and 202 ms; both showed 10 MB billed. This does not demonstrate lower latency or billed bytes, and it does not isolate clustering benefits.
- **Python:** The BigQuery client returned the expected summary with caching disabled and a 50 MiB query billing-data limit.
- **Tableau:** The dashboard uses ten aggregate groups and calculates churn as `SUM(churned_users) / SUM(users)`. Select a bar in the first chart to filter the charts below.

[Cloud reproduction guide](docs/bigquery_tableau.md) · [Feature parity report](reports/bigquery_feature_parity.csv) · [Scan comparison](reports/bigquery_scan_comparison.csv) · [Dashboard data](reports/tableau/kkbox_transaction_segments.csv)

## Model Results

Historical training contains 882,127 users; later evaluation contains 970,960 users. Training outcomes are observed before the later feature cutoff.

| Model | Log Loss ↓ | ROC-AUC ↑ | Average Precision ↑ |
|---|---:|---:|---:|
| Logistic Regression | **0.2073** | **0.8499** | **0.5501** |
| LightGBM | 0.2255 | 0.8395 | 0.4941 |
| XGBoost | 0.2300 | 0.8392 | 0.4896 |
| GRU + transaction inputs | 0.2398 | 0.8091 | 0.4702 |

![Model comparison](reports/figures/final_model_comparison.png)

Logistic Regression was the strongest benchmark in this evaluation. Adding listening features reduced its Log Loss by **2.64%**. Historical internal hyperparameter tuning did not improve the tree models' later-period results.

The GRU uses 30-day listening sequences and transaction inputs. Its epoch count was selected using historical internal validation, followed by refitting on all historical users. It did not outperform the classical baselines.

[Feature comparison](reports/behavior_feature_comparison.csv) · [Tuning results](reports/tuning_comparison.csv) · [GRU configuration](reports/gru_training_config.json)

## Risk Targeting and Retention Insight

The combined-feature Logistic Regression's highest-risk 10% of users achieved:

- **53.50% Precision@10%**
- **59.49% Recall@10%**
- **5.95 Lift@10%**

Previously active users with no logs in the most recent seven days had **13.89% churn**, compared with **9.32%** among the established-activity reference group with stable or increased recorded plays.

![Retention segment](reports/figures/retention_target_segment.png)

The target requires at least four recorded days and 20 recorded plays in the preceding seven-day window. The later cohort contains 5,041 such users.

This association motivates testing personalized recommendations or re-engagement reminders after verifying logging, subscription, and contact eligibility. It does not establish a causal retention effect.

[Segment analysis](notebooks/13_retention_segments.ipynb) · [Risk targeting results](reports/risk_targeting_results.csv)

## Retention Decision Optimization

Extended churn prediction with a **Pyomo/Gurobi mixed-integer allocation prototype** on a deterministic 750-user sample, using simulated intervention effects and contribution margins. Compared risk-priority targeting, upgrade-aware value/cost greedy, and 100 random allocations across four budgets. Added single-stage maximin robustness over three intervention-effect scenarios.

At a budget of 120 hypothetical units, nominal optimization produced **11.7% higher simulated expected net value than risk-priority targeting** and matched the upgrade-aware greedy strategy. Robust allocation improved the weakest modeled scenario's value by **5.9%** relative to nominal allocation. Neither result measures actual retention or real profit. All eight solver runs were optimal and checked for budget/capacity feasibility; small cases were independently verified by enumeration.

![Retention allocation: base and worst-scenario simulated net value across budgets](reports/optimization/budget_sensitivity.png)

Left: simulated expected net value under base assumptions. Right: net value in the weakest modeled scenario. Nominal MILP and upgrade-aware value/cost greedy overlap in these instances; all intervention economics are simulated.

[Completed results notebook](notebooks/18_retention_optimization_results.ipynb) · [Model, assumptions, and reproduction](docs/retention_optimization.md) · [Strategy results](reports/optimization/strategy_summary.csv)

## Proposed Randomized Experiment

The user-level 1:1 design specifies intention-to-treat analysis and a fixed renewal observation endpoint.

Using a historical baseline of 13.89%, a **2-percentage-point absolute reduction**, two-sided α=0.05, and 80% power requires approximately **4,400 users per arm**, or **8,800 total**.

The historical candidate pool is insufficient for this planning target and has not undergone prospective eligibility checks. No intervention was delivered.

[Experiment plan](reports/retention_experiment_plan.md) · [Power analysis](reports/retention_power_analysis.csv)

## Data and Evaluation Design

Source: [WSDM — KKBOX's Churn Prediction Challenge](https://www.kaggle.com/competitions/kkbox-churn-prediction-challenge/data).

Original transactions and listening logs cover January 2015 through February 2017. Full files were scanned for auditing; only relevant users and windows were extracted for modeling.

| Cohort | Feature cutoff | Transaction window | Listening window |
|---|---|---|---|
| Historical training | 2016-11-30 | 90 days | 30 days |
| Later evaluation | 2017-02-28 | 90 days | 30 days |

Historical December 2016 labels were reconstructed using the provided labeling example, with outcomes observed through January 30, 2017. A renewal gap of at least 30 days, or no observed renewal, is classified as churn. Later evaluation uses the supplied `train_v2` labels.

Raw data, user-level derived files, and model weights are excluded from Git.

## Reproduce

Use Python 3.11 and install the recorded dependencies:

```bash
python -m pip install -r requirements.txt
jupyter lab
```

Obtain the official data and follow [the reproduction guide](docs/reproduction.md). Notebooks are organized in numbered stages; reports can be inspected without downloading raw data.

## Limitations

- Historical reconstructed labels and official later labels have different provenance; exact label parity and official generation parameters were not independently verified.
- Point-in-time source snapshots were not verified. This is retrospective cohort evaluation, not a verified deployment simulation.
- The later cohort was inspected repeatedly and is not an untouched independent test.
- GRU and classical models use different representations, so the comparison does not isolate architecture or sequence-order effects.
- Predictive lift and segment differences do not measure intervention effectiveness.

## Repository

- `notebooks/`: numbered analysis, modeling, and experiment-design stages
- `sql/`: queries used by the notebooks
- `sql/bigquery/`: cloud audit, partitioning, feature engineering, and dashboard queries
- `scripts/`: sample preparation, SQL parity verification, and a BigQuery Python query
- `reports/`: aggregate results, configurations, figures, and experiment plan
- `docs/`: reproduction instructions
- `requirements.txt`: recorded local analysis dependencies
- `requirements-bigquery.txt`: additional dependency for the optional cloud Python query
