# BigQuery and Tableau status

The sample transaction extension is complete and the Tableau dashboard is published.
See [the reproduction guide](bigquery_tableau.md) for the final workflow and evidence.

- Verified 10,000-user cohort and 27,094 source transactions.
- Replaced expired historical date partitions with month-index range partitions.
- Verified seven features and the label against the original DuckDB SQL.
- Recorded uncached January scans: 635.02 KB versus 218.32 KB.
- Confirmed authenticated Python client execution.
- Verified ten aggregate dashboard groups and weighted churn calculations.
- User demonstrated chart filtering; the signed-out public page renders successfully.
- README links to the public dashboard and aggregate validation reports.

[Published dashboard](https://public.tableau.com/app/profile/becca.xu/viz/KKBoxChurnOverviewBigQueryTableau/KKBoxChurnOverview)

This is a transaction sample exercise. Listening SQL and model training were not
migrated to BigQuery. The extension has been committed and pushed to GitHub.
