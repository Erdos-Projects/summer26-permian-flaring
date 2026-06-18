import pandas as pd
import plotly.graph_objects as go
import os

# ==========================================
# 1. SETUP & LOAD DATA
# ==========================================
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
interim_dir = os.path.join(project_root, 'data/interim/new-mexico')
viz_dir = os.path.join(project_root, 'visualizations/new-mexico')

print("Loading Historical Time-Series Data...")
df_basin = pd.read_csv(os.path.join(interim_dir, 'master_basin_timeseries_2012_2026.csv'))
df_site = pd.read_csv(os.path.join(interim_dir, 'master_site_timeseries_2012_2026.csv'))

df_basin['Date'] = pd.to_datetime(df_basin['Date'])
df_site['Date'] = pd.to_datetime(df_site['Date'])

# ==========================================
# 2. BASIN-WIDE HISTORICAL DASHBOARD
# ==========================================
print("Building Basin-Wide Historical Dashboard...")
fig_basin = go.Figure()

fig_basin.add_trace(go.Scatter(
    x=df_basin['Date'], y=df_basin['Basin_VIIRS_Normalized_MW'],
    mode='lines+markers', name='Normalized VIIRS Heat (MW/Obs)',
    line=dict(color='#ff4500', width=3)
))
fig_basin.add_trace(go.Scatter(
    x=df_basin['Date'], y=df_basin['Basin_Reported_Flared_MCF'],
    mode='lines+markers', name='Reported Flared (MCF)',
    line=dict(color='#00f0ff', width=2, dash='dot'), yaxis='y2'
))
fig_basin.add_trace(go.Scatter(
    x=df_basin['Date'], y=df_basin['Basin_Reported_Oil_BBL'],
    mode='lines+markers', name='Reported Oil (BBL)',
    line=dict(color='#00ff66', width=2, dash='dash'), yaxis='y3'
))

fig_basin.update_layout(
    title=dict(text="Permian Basin Macro Audit: 14-Year Historical Profile (2012-2026)", y=0.98),
    template="plotly_dark",
    xaxis=dict(domain=[0.0, 0.85], title="Date"), 
    yaxis=dict(title=dict(text="Normalized VIIRS (MW/Obs)", font=dict(color="#ff4500")), tickfont=dict(color="#ff4500")),
    yaxis2=dict(title=dict(text="Reported Flared (MCF)", font=dict(color="#00f0ff")), tickfont=dict(color="#00f0ff"), anchor="x", overlaying="y", side="right"),
    yaxis3=dict(title=dict(text="Reported Oil (BBL)", font=dict(color="#00ff66")), tickfont=dict(color="#00ff66"), anchor="free", overlaying="y", side="right", position=0.95),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    hovermode="x unified"
)
basin_html = os.path.join(viz_dir, 'interactive_basin_aggregate.html')
fig_basin.write_html(basin_html)

# ==========================================
# 3. SITE-LEVEL HISTORICAL DASHBOARD
# ==========================================
print("Building Site-Level Historical Dashboard...")
unique_sites = sorted(df_site['EOG_Site_ID'].unique().astype(int))

fig_site = go.Figure()
traces_per_site = 3 

for site in unique_sites:
    site_data = df_site[df_site['EOG_Site_ID'] == site]
    
    fig_site.add_trace(go.Scatter(
        x=site_data['Date'], y=site_data['VIIRS_Normalized_MW'],
        mode='lines+markers', name='Normalized VIIRS Heat (MW/Obs)',
        line=dict(color='#ff4500', width=2), visible=(site == unique_sites[0])
    ))
    fig_site.add_trace(go.Scatter(
        x=site_data['Date'], y=site_data['Reported_Flared_MCF'],
        mode='lines+markers', name='Reported Flared (MCF)',
        line=dict(color='#00f0ff', width=2, dash='dot'), yaxis='y2', visible=(site == unique_sites[0])
    ))
    fig_site.add_trace(go.Scatter(
        x=site_data['Date'], y=site_data['Reported_Oil_Produced_BBL'],
        mode='lines', name='Reported Oil (BBL)',
        line=dict(color='#00ff66', width=2, dash='dash'), yaxis='y3', visible=(site == unique_sites[0])
    ))

dropdown_buttons = []
for i, site in enumerate(unique_sites):
    visibility = [False] * (len(unique_sites) * traces_per_site)
    visibility[i*traces_per_site : (i+1)*traces_per_site] = [True, True, True]
    button = dict(label=f"Site {site}", method="update", args=[{"visible": visibility}, {"title": dict(text=f"Temporal Audit Profile: EOG Site {site} (2012-2026)")}])
    dropdown_buttons.append(button)

fig_site.update_layout(
    title=dict(text=f"Temporal Audit Profile: EOG Site {unique_sites[0]} (2012-2026)", y=0.98),
    template="plotly_dark",
    updatemenus=[dict(active=0, buttons=dropdown_buttons, x=0.0, y=1.15, xanchor="left", yanchor="top")],
    xaxis=dict(domain=[0.0, 0.85], title="Date"),
    yaxis=dict(title=dict(text="Normalized VIIRS (MW/Obs)", font=dict(color="#ff4500")), tickfont=dict(color="#ff4500")),
    yaxis2=dict(title=dict(text="Reported Flared (MCF)", font=dict(color="#00f0ff")), tickfont=dict(color="#00f0ff"), anchor="x", overlaying="y", side="right"),
    yaxis3=dict(title=dict(text="Reported Oil (BBL)", font=dict(color="#00ff66")), tickfont=dict(color="#00ff66"), anchor="free", overlaying="y", side="right", position=0.95),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
    hovermode="x unified"
)
site_html = os.path.join(viz_dir, 'interactive_site_widget.html')
fig_site.write_html(site_html)

print("\nDashboards ready! Open in Safari/Chrome.")