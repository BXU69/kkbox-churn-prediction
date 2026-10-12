# Reproduction Guide

## Environment

Development used Python 3.11 on an Apple Silicon Mac. PyTorch training used MPS. Cross-platform installation and a full fresh-environment rerun have not been verified.

Create an isolated environment and install the recorded dependencies:

```bash
conda create -n kkbox-churn python=3.11 pip
conda activate kkbox-churn
python -m pip install -r requirements.txt
```

On macOS, install the OpenMP runtime for the tree-model libraries if needed:

```bash
brew install libomp
```

Launch JupyterLab from the repository root:

```bash
jupyter lab
```

## Required Data

Obtain files from the official competition under its rules. Place these in `data/raw/`:

- `train.csv`
- `train_v2.csv`
- `members_v3.csv`
- `transactions.csv`
- `transactions_v2.csv`
- `WSDMChurnLabeller.scala`
- `user_logs.csv.7z`

Extract the label, member, and transaction files before starting. Notebook 09 inspects and extracts `user_logs.csv.7z`; it currently requires the archive even when the extracted CSV already exists.

The raw listening CSV occupies approximately 28.42 GiB. Plan for about 50 GiB of free disk space for a full initial run, including archives, extracted files, derived data, and temporary work.

## Execution Order

Run notebook cells from top to bottom. Each notebook must run in its own kernel without relying on variables from another notebook.

| Notebooks | Purpose |
|---|---|
| 01–03 | Label/member/transaction audits and initial transaction features |
| 04 | Random-holdout baseline |
| 05–06 | Historical labels, historical features, and later-cohort evaluation |
| 07–08 | Classical model comparison and internal historical tuning |
| 09–10 | Full listening audit and extracted daily windows |
| 11–12 | Combined features, model evaluation, duration sensitivity, and targeting |
| 13–14 | Behavioral segments and proposed experiment power analysis |
| 15–16 | Aligned sequences, GRU selection, full historical refit, and evaluation |
| 17 | Final figures and presentation cleanup |

The SQL files use tables or views registered by their notebooks; they are not standalone database pipelines.

Close completed kernels to release memory. Do not run large extraction or training stages concurrently.

## Local Outputs

- `data/processed/`: feature tables, daily Parquet partitions, and sequence arrays
- `models/`: GRU weights and fitted preprocessing
- `reports/`: aggregate results and configurations

Only the reports and source files belong in Git.

Listening extraction and sequence construction use completion checkpoints. If inputs or configuration change, the notebooks reject incompatible outputs. If a run is interrupted, inspect the incomplete output directory before rebuilding; do not treat partial files as completed data.

## Verification and Recorded Results

Check the saved assertions and reports for:

- Complete cohort retention after feature joins
- Unique user-day records in extracted listening windows
- Sequence/user/label alignment
- Training-only preprocessing during model selection
- Historical training outcomes ending before the later feature cutoff

The notebooks were run during development. The documented full workflow has not yet been independently validated in a clean environment. Package versions, platform differences, and GPU operations can affect runtime and numerical results.

## Data Cleanup

Keep raw data until the required derived files have been verified. Deleting the raw CSV prevents earlier audit and extraction stages from running until it is restored.

Retaining the compressed listening archive allows re-extraction. Derived sequences alone do not replace the raw data for reproducing earlier stages.