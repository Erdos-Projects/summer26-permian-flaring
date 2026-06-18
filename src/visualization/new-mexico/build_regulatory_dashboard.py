import pandas as pd
import plotly.graph_objects as go
import os

# ==========================================
# 1. LOAD DATA
# ==========================================
project_root = os.path.expanduser('~/work/projects/summer26-permian-flaring')
interim_dir = os.path.join(project_root, 'data/interim/new-mexico')
viz_dir = os.path.join(project_root, 'visualizations')

os.makedirs(viz_dir, exist_ok=True)

print("Loading Master Time-Series Dataset...")
df = pd.read_csv(os.path.join(interim_dir, 'master_regulatory_timeseries_2021_2026.csv'))
df['Date'] = pd.to_datetime(df['Date'])

# Get list of unique sites and ensure they are integers for clean reading
unique_sites = sorted(df['EOG_Site_ID'].unique().astype(int))

# ==========================================
# 2. INITIALIZE PLOTLY FIGURE
# ==========================================
print(f"Building interactive widget for {len(unique_sites)} EOG Sites...")

fig = go.Figure()
traces_per_site = 2 

for site in unique_sites:
    site_data = df[df['EOG_Site_ID'] == site]
    
    # Trace 1: Reported Gas Produced (Primary Left Y-Axis)
    fig.add_trace(go.Scatter(
        x=site_data['Date'], y=site_data['Reported_Produced_MCF'],
        mode='lines+markers', name='Gas Produced (MCF)',
        line=dict(color='#00ff66', width=2),
        visible=(site == unique_sites[0])
    ))
    
    # Trace 2: Reported Flared MCF (Secondary Right Y-Axis)
    fig.add_trace(go.Scatter(
        x=site_data['Date'], y=site_data['Reported_Flared_MCF'],
        mode='lines+markers', name='Flared Waste (MCF)',
        line=dict(color='#ff4500', width=2, dash='dot'),
        yaxis='y2',
        visible=(site == unique_sites[0])
    ))

# ==========================================
# 3. BUILD DROPDOWN MENU LOGIC
# ==========================================
dropdown_buttons = []

for i, site in enumerate(unique_sites):
    # Boolean array to turn ON the 2 traces for the selected site, and turn OFF all others
    visibility = [False] * (len(unique_sites) * traces_per_site)
    visibility[i*traces_per_site : (i+1)*traces_per_site] = [True, True]
    
    button = dict(
        label=f"EOG Site {site}",
        method="update",
        args=[{"visible": visibility},
              {"title": f"Regulatory Production vs Waste: EOG Site {site}"}]
    )
    dropdown_buttons.append(button)

# ==========================================
# 4. LAYOUT & STYLING
# ==========================================
fig.update_layout(
    title=f"Regulatory Production vs Waste: EOG Site {unique_sites[0]}",
    template="plotly_dark",
    updatemenus=[dict(
        active=0,
        buttons=dropdown_buttons,
        x=1.15, y=1.1, 
        xanchor="right", yanchor="top"
    )],
    xaxis=dict(title="Date"),
    yaxis=dict(
        title=dict(
            text="Reported Gas Produced (MCF)",
            font=dict(color="#00ff66")
        ),
        tickfont=dict(color="#00ff66")
    ),
    yaxis2=dict(
        title=dict(
            text="Reported Flared Waste (MCF)",
            font=dict(color="#ff4500")
        ),
        tickfont=dict(color="#ff4500"),
        anchor="x",
        overlaying="y",
        side="right" 
    ),
    legend=dict(x=1.15, y=0.5),
    hovermode="x unified" 
)

# ==========================================
# 5. EXPORT
# ==========================================
output_html = os.path.join(viz_dir, 'interactive_regulatory_widget.html')
fig.write_html(output_html)

print("\n" + "="*60)
print(f"Interactive Regulatory Widget successfully generated!")
print(f"Open this file in Safari/Chrome: {output_html}")
print("="*60)