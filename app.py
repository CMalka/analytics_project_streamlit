"""
NYC Citywide Payroll Explorer
Streamlit dashboard for the Citywide Payroll Data (Fiscal Year) dataset.

Run with:
    streamlit run app.py

Expects either `Citywide_Payroll_Data__Fiscal_Year_.csv` in the same folder,
or a `data/` subfolder containing per-year gzipped CSVs (`fy2014.csv.gz`,
`fy2015.csv.gz`, ...). Point to a different location with the file path box
that appears if neither is found.
"""

import glob
import os
import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------------------------------
# Page setup
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="NYC Citywide Payroll Explorer",
    page_icon="\U0001F4CA",
    layout="wide",
)

DEFAULT_CSV_NAME = "Citywide_Payroll_Data__Fiscal_Year_.csv"
DEFAULT_DATA_DIR = "data"  # holds split fy*.csv.gz files, if used instead


# --------------------------------------------------------------------------
# Data loading & cleaning (cached so the 400MB+ dataset is only parsed once)
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading and cleaning payroll data (first run only)...")
def load_data(csv_paths) -> pd.DataFrame:
    """csv_paths: a single path (str) or a list of paths. Each may be a plain
    .csv or a .csv.gz (pandas infers gzip from the extension automatically)."""
    if isinstance(csv_paths, str):
        csv_paths = [csv_paths]

    dtypes = {
        "Fiscal Year": "int16",
        "Agency Name": "category",
        "Last Name": "string",
        "First Name": "string",
        "Mid Init": "string",
        "Work Location Borough": "category",
        "Title Description": "category",
        "Leave Status as of June 30": "category",
        "Pay Basis": "category",
    }

    chunks = []
    for path in csv_paths:
        for chunk in pd.read_csv(path, dtype=dtypes, chunksize=300_000):
            chunk.columns = (
                chunk.columns.str.strip().str.lower().str.replace(" ", "_")
            )
            for c in ["agency_name", "title_description", "work_location_borough"]:
                chunk[c] = chunk[c].astype(str).str.strip()

            for c in ["base_salary", "regular_gross_paid", "total_ot_paid", "total_other_pay"]:
                chunk[c] = (
                    chunk[c]
                    .astype(str)
                    .str.replace("$", "", regex=False)
                    .str.replace(",", "", regex=False)
                    .astype(float)
                )

            chunk["total_paid"] = (
                chunk["regular_gross_paid"] + chunk["total_ot_paid"] + chunk["total_other_pay"]
            )
            chunk["agency_start_date"] = pd.to_datetime(
                chunk["agency_start_date"], errors="coerce"
            )
            chunk["full_name"] = (
                chunk["first_name"].astype(str).str.strip()
                + " "
                + chunk["last_name"].astype(str).str.strip()
            )

            chunks.append(chunk)

    df = pd.concat(chunks, ignore_index=True)
    df["fiscal_year"] = df["fiscal_year"].astype(int)
    return df


def fmt_money(x: float) -> str:
    if pd.isna(x):
        return "$0"
    if abs(x) >= 1_000_000_000:
        return f"${x/1_000_000_000:,.2f}B"
    if abs(x) >= 1_000_000:
        return f"${x/1_000_000:,.1f}M"
    if abs(x) >= 1_000:
        return f"${x/1_000:,.0f}K"
    return f"${x:,.0f}"


# --------------------------------------------------------------------------
# Locate & load the data: single CSV, split gz files in data/, or user path
# --------------------------------------------------------------------------
st.title("\U0001F4CA NYC Citywide Payroll Explorer")

split_files = sorted(glob.glob(os.path.join(DEFAULT_DATA_DIR, "fy*.csv*")))

if os.path.exists(DEFAULT_CSV_NAME):
    data_source = DEFAULT_CSV_NAME
elif split_files:
    data_source = split_files
else:
    st.warning(
        f"Couldn't find **{DEFAULT_CSV_NAME}** or a `{DEFAULT_DATA_DIR}/` folder "
        "of split files next to app.py. Enter a full path below (a single CSV, "
        "or a folder containing fy*.csv.gz files)."
    )
    user_path = st.text_input("Path to CSV file or data folder", value="")
    if not user_path or not os.path.exists(user_path):
        st.stop()
    if os.path.isdir(user_path):
        data_source = sorted(glob.glob(os.path.join(user_path, "fy*.csv*")))
        if not data_source:
            st.error("No fy*.csv / fy*.csv.gz files found in that folder.")
            st.stop()
    else:
        data_source = user_path

df = load_data(data_source)
years = sorted(df["fiscal_year"].unique().tolist())

# --------------------------------------------------------------------------
# Sidebar filters (apply everywhere: KPI header, overview, and year tabs)
# --------------------------------------------------------------------------
st.sidebar.header("Filters")

agencies = st.sidebar.multiselect(
    "Agency", sorted(df["agency_name"].unique().tolist())
)
boroughs = st.sidebar.multiselect(
    "Work borough", sorted(df["work_location_borough"].unique().tolist())
)
statuses = st.sidebar.multiselect(
    "Leave status", sorted(df["leave_status_as_of_june_30"].unique().tolist())
)
pay_basis = st.sidebar.multiselect(
    "Pay basis", sorted(df["pay_basis"].unique().tolist())
)
name_search = st.sidebar.text_input("Search name or title contains")

filtered = df
if agencies:
    filtered = filtered[filtered["agency_name"].isin(agencies)]
if boroughs:
    filtered = filtered[filtered["work_location_borough"].isin(boroughs)]
if statuses:
    filtered = filtered[filtered["leave_status_as_of_june_30"].isin(statuses)]
if pay_basis:
    filtered = filtered[filtered["pay_basis"].isin(pay_basis)]
if name_search:
    s = name_search.lower()
    filtered = filtered[
        filtered["full_name"].str.lower().str.contains(s, na=False)
        | filtered["title_description"].str.lower().str.contains(s, na=False)
    ]

st.sidebar.caption(f"{len(filtered):,} of {len(df):,} records match your filters.")

# --------------------------------------------------------------------------
# Top-of-app KPI strip (reflects current filters, across all years)
# --------------------------------------------------------------------------
k1, k2, k3, k4, k5, k6 = st.columns(6)
k1.metric("Employee records", f"{len(filtered):,}")
k2.metric("Total gross paid", fmt_money(filtered["total_paid"].sum()))
k3.metric("Avg base salary", fmt_money(filtered["base_salary"].mean()))
k4.metric("Total overtime paid", fmt_money(filtered["total_ot_paid"].sum()))
k5.metric("Agencies", f"{filtered['agency_name'].nunique():,}")
k6.metric("Fiscal years", f"{filtered['fiscal_year'].nunique()}")

st.divider()

# --------------------------------------------------------------------------
# Tabs: Overview (cross-year trends) + one tab per fiscal year
# --------------------------------------------------------------------------
tab_labels = ["\U0001F4C8 Overview"] + [f"FY {y}" for y in years] + ["\U0001F50E Employee Lookup"]
tabs = st.tabs(tab_labels)

# ---- Overview tab: cross-year trends -------------------------------------
with tabs[0]:
    st.subheader("Citywide trends across fiscal years")

    by_year = (
        filtered.groupby("fiscal_year", as_index=False)
        .agg(
            headcount=("full_name", "size"),
            total_paid=("total_paid", "sum"),
            avg_base_salary=("base_salary", "mean"),
            total_ot_paid=("total_ot_paid", "sum"),
        )
        .sort_values("fiscal_year")
    )
    by_year["fiscal_year"] = by_year["fiscal_year"].astype(str)

    c1, c2 = st.columns(2)
    with c1:
        fig = px.bar(
            by_year, x="fiscal_year", y="total_paid",
            title="Total payroll spend by fiscal year", text_auto=".2s",
        )
        fig.update_layout(yaxis_title="Total paid ($)", xaxis_title="Fiscal year")
        st.plotly_chart(fig, use_container_width=True)
    with c2:
        fig = px.line(
            by_year, x="fiscal_year", y="headcount", markers=True,
            title="Headcount by fiscal year",
        )
        fig.update_layout(yaxis_title="Employee records", xaxis_title="Fiscal year")
        st.plotly_chart(fig, use_container_width=True)

    c3, c4 = st.columns(2)
    with c3:
        fig = px.line(
            by_year, x="fiscal_year", y="avg_base_salary", markers=True,
            title="Average base salary by fiscal year",
        )
        fig.update_layout(yaxis_title="Avg base salary ($)", xaxis_title="Fiscal year")
        st.plotly_chart(fig, use_container_width=True)
    with c4:
        fig = px.bar(
            by_year, x="fiscal_year", y="total_ot_paid",
            title="Total overtime paid by fiscal year", text_auto=".2s",
        )
        fig.update_layout(yaxis_title="Total OT paid ($)", xaxis_title="Fiscal year")
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Top 15 agencies by total pay (across all selected years)")
    top_agencies = (
        filtered.groupby("agency_name", as_index=False)
        .agg(total_paid=("total_paid", "sum"), headcount=("full_name", "size"))
        .sort_values("total_paid", ascending=False)
        .head(15)
    )
    fig = px.bar(
        top_agencies.sort_values("total_paid"),
        x="total_paid", y="agency_name", orientation="h",
        title=None, text_auto=".2s",
    )
    fig.update_layout(xaxis_title="Total paid ($)", yaxis_title="")
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("#### Borough distribution")
    borough_counts = filtered["work_location_borough"].value_counts().reset_index()
    borough_counts.columns = ["borough", "employees"]
    fig = px.pie(borough_counts, names="borough", values="employees", hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

# ---- One tab per fiscal year ----------------------------------------------
for i, y in enumerate(years, start=1):
    with tabs[i]:
        yr_df = filtered[filtered["fiscal_year"] == y]
        st.subheader(f"Fiscal Year {y}")

        if yr_df.empty:
            st.info("No records for this year match the current filters.")
            continue

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Employees", f"{len(yr_df):,}")
        c2.metric("Total paid", fmt_money(yr_df["total_paid"].sum()))
        c3.metric("Avg base salary", fmt_money(yr_df["base_salary"].mean()))
        c4.metric("Avg OT paid / employee", fmt_money(yr_df["total_ot_paid"].mean()))

        colA, colB = st.columns(2)
        with colA:
            st.markdown("**Top 10 agencies by total pay**")
            top_a = (
                yr_df.groupby("agency_name", as_index=False)
                .agg(total_paid=("total_paid", "sum"), headcount=("full_name", "size"))
                .sort_values("total_paid", ascending=False)
                .head(10)
            )
            fig = px.bar(
                top_a.sort_values("total_paid"), x="total_paid", y="agency_name",
                orientation="h", text_auto=".2s",
            )
            fig.update_layout(xaxis_title="Total paid ($)", yaxis_title="", height=400)
            st.plotly_chart(fig, use_container_width=True)

        with colB:
            st.markdown("**Top 10 job titles by headcount**")
            top_t = (
                yr_df.groupby("title_description", as_index=False)
                .size()
                .sort_values("size", ascending=False)
                .head(10)
            )
            fig = px.bar(
                top_t.sort_values("size"), x="size", y="title_description",
                orientation="h",
            )
            fig.update_layout(xaxis_title="Employees", yaxis_title="", height=400)
            st.plotly_chart(fig, use_container_width=True)

        colC, colD = st.columns(2)
        with colC:
            st.markdown("**Base salary distribution** (per Annum only)")
            annum = yr_df[yr_df["pay_basis"] == "per Annum"]
            fig = px.histogram(annum, x="base_salary", nbins=50)
            fig.update_layout(xaxis_title="Base salary ($)", yaxis_title="Employees")
            st.plotly_chart(fig, use_container_width=True)

        with colD:
            st.markdown("**Pay basis breakdown**")
            pb = yr_df["pay_basis"].value_counts().reset_index()
            pb.columns = ["pay_basis", "employees"]
            fig = px.pie(pb, names="pay_basis", values="employees", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("**Top 15 highest-paid employees**")
        top_paid = yr_df.sort_values("total_paid", ascending=False).head(15)[
            ["full_name", "agency_name", "title_description", "base_salary",
             "total_ot_paid", "total_paid"]
        ]
        st.dataframe(top_paid, use_container_width=True, hide_index=True)

        with st.expander(f"Browse all {len(yr_df):,} FY{y} records"):
            st.dataframe(
                yr_df[
                    ["full_name", "agency_name", "title_description",
                     "work_location_borough", "leave_status_as_of_june_30",
                     "pay_basis", "base_salary", "regular_gross_paid",
                     "total_ot_paid", "total_other_pay", "total_paid"]
                ].sort_values("total_paid", ascending=False),
                use_container_width=True,
                hide_index=True,
                height=400,
            )
            st.download_button(
                f"Download FY{y} filtered data as CSV",
                yr_df.to_csv(index=False).encode("utf-8"),
                file_name=f"payroll_fy{y}_filtered.csv",
                mime="text/csv",
            )

# ---- Employee lookup tab ---------------------------------------------------
with tabs[-1]:
    st.subheader("Look up an individual employee across years")
    q = st.text_input("Search by first or last name")
    if q:
        matches = filtered[
            filtered["full_name"].str.lower().str.contains(q.lower(), na=False)
        ].sort_values(["full_name", "fiscal_year"])
        st.write(f"{matches['full_name'].nunique()} matching people, {len(matches):,} records")
        st.dataframe(
            matches[
                ["fiscal_year", "full_name", "agency_name", "title_description",
                 "work_location_borough", "base_salary", "total_paid"]
            ],
            use_container_width=True,
            hide_index=True,
        )
        if not matches.empty and matches["full_name"].nunique() == 1:
            fig = px.line(
                matches, x="fiscal_year", y="total_paid", markers=True,
                title="Total pay by year",
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Type a name above to see their pay history across fiscal years.")
