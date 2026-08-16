import pandas as pd

path = '/sessions/youthful-sleepy-lovelace/mnt/uploads/Citywide_Payroll_Data__Fiscal_Year_.csv'

dtypes = {
    'Fiscal Year': 'int16', 'Agency Name': 'category', 'Last Name': 'string', 'First Name': 'string',
    'Mid Init': 'string', 'Work Location Borough': 'category', 'Title Description': 'category',
    'Leave Status as of June 30': 'category', 'Pay Basis': 'category'
}

chunks = []
for chunk in pd.read_csv(path, dtype=dtypes, chunksize=300000):
    chunk.columns = chunk.columns.str.strip().str.lower().str.replace(' ', '_')
    for c in ['agency_name', 'title_description', 'work_location_borough']:
        chunk[c] = chunk[c].astype(str).str.strip()
    for c in ['base_salary', 'regular_gross_paid', 'total_ot_paid', 'total_other_pay']:
        chunk[c] = (
            chunk[c].astype(str)
            .str.replace('$', '', regex=False)
            .str.replace(',', '', regex=False)
            .astype(float)
        )
    chunk['total_paid'] = chunk['regular_gross_paid'] + chunk['total_ot_paid'] + chunk['total_other_pay']
    chunk['agency_start_date'] = pd.to_datetime(chunk['agency_start_date'], errors='coerce')

    keep = ['fiscal_year', 'agency_name', 'last_name', 'first_name', 'mid_init', 'agency_start_date',
            'work_location_borough', 'title_description', 'leave_status_as_of_june_30', 'base_salary',
            'pay_basis', 'regular_hours', 'regular_gross_paid', 'ot_hours', 'total_ot_paid',
            'total_other_pay', 'total_paid']
    chunks.append(chunk[keep])

df = pd.concat(chunks, ignore_index=True)
print(df.shape)
print(round(df.memory_usage(deep=True).sum() / 1e6, 1), 'MB in memory')

df.to_pickle('/sessions/youthful-sleepy-lovelace/mnt/outputs/payroll_clean.pkl')
print('saved payroll_clean.pkl')
