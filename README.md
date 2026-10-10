# KKBOX Customer Churn Prediction

An ongoing portfolio project exploring customer churn through SQL, Python, predictive modeling, and retention experiment design.

## Current Progress

Completed an initial audit of the churn labels and member data. Modeling and experiment design are planned.

### Initial Findings

- `train.csv`: 992,931 users; 6.39% churn.
- `train_v2.csv`: 970,960 users; 8.99% churn.
- Both label tables have unique user IDs and no missing or invalid labels.
- 11.33% of `train_v2` users have no matching member record.
- Churn is 5.35% among unmatched users and 9.46% among matched users. This is a descriptive association, not a causal finding.
- All labeled users are retained. Unusable ages are treated as missing, and missing gender values are represented as `unknown`.

![Churn by member record availability](reports/figures/churn_by_member_availability.png)

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
