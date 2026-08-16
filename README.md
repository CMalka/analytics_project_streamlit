# NYC Citywide Payroll Explorer

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py
```

Either put `Citywide_Payroll_Data__Fiscal_Year_.csv` in the same folder as
`app.py`, or put the split, gzipped files (`data/fy2014.csv.gz`, etc. — see
below) in a `data/` subfolder. The app checks for the single CSV first, then
falls back to `data/`, then asks for a path. First load takes ~30-60s to
clean 2.2M rows; after that it's cached for the session.

### Uploading the data to GitHub if the raw CSV is too big

The raw CSV is ~414MB — too big for most upload limits (GitHub itself blocks
anything over 100MB via plain git). Two options:

- **Split by year + gzip** (already done for you in `data/`): each
  `fy20XX.csv.gz` is ~12-15MB, under a 25MB cap. Commit the `data/` folder
  instead of the raw CSV — the app reads it automatically.
- **Don't commit the data at all** (cleanest option): add `*.csv` and
  `Citywide_Payroll_Data__Fiscal_Year_.csv` to `.gitignore`, and note in your
  README that users should download it from
  [NYC Open Data](https://data.cityofnewyork.us/) and drop it next to
  `app.py`. Repos generally shouldn't carry data they don't own.

## What's in the app

- **KPI strip at top** — employee count, total gross paid, avg base salary,
  total OT paid, agency count, year count — updates live with your filters.
- **Sidebar filters** — agency, borough, leave status, pay basis, name/title
  search — apply across every tab.
- **Overview tab** — trends across all 4 fiscal years (2014-2017): payroll
  spend, headcount, avg salary, OT spend, top agencies, borough split.
- **One tab per fiscal year** — that year's KPIs, top agencies, top titles,
  salary distribution, pay-basis split, top 15 highest-paid employees, and a
  browsable/downloadable full table.
- **Employee Lookup tab** — search a name, see their pay history across years.

## Data quality note

Some agency names appear twice with different casing (e.g. `POLICE DEPARTMENT`
vs `Police Department`), which splits their totals. Worth normalizing
(`.str.upper()`) if you want exact agency totals.

## Ideas to explore further

- **Pay equity by title** — for a given title, compare base salary spread
  across agencies or boroughs to spot outliers.
- **Overtime dependency** — rank employees/titles by OT-as-%-of-total-pay;
  flag titles where OT regularly exceeds base pay.
- **Tenure vs. pay** — use `agency_start_date` to compute tenure and check
  whether pay scales with years of service, by title.
- **Headcount churn** — compare who's ACTIVE vs CEASED year over year to
  estimate turnover by agency.
- **Cost per resident/service** — pair agency payroll totals with public
  headcount or budget data for cost-effectiveness comparisons.
- **Anomaly detection** — flag records with unusually high OT hours relative
  to regular hours, or base salary jumps that don't match a title change.
- **Geographic view** — map total pay or headcount by `work_location_borough`
  (a simple choropleth if you add borough boundary data).
- **Multi-year employee tracking** — the Employee Lookup tab is a start; could
  extend to promotion detection (title changes year over year).
- **Normalize duplicate agency names** — clean up casing inconsistencies
  (see note above) before trusting agency-level totals.
