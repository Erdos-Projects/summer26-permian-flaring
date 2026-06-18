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
df = pd.read_csv(os.path.join(interim_dir, 'master_site_timeseries_2021_2026.csv'))
df['Date'] = pd.to_datetime(df['Date'])

# Get list of unique sites, sort them, and ensure they are integers for clean reading
unique_sites = sorted(df['EOG_Site_ID'].unique().astype(int))

# ==========================================
# 2. INITIALIZE PLOTLY FIGURE
# ==========================================
print(f"Building interactive widget for {len(unique_sites)} EOG Sites...")

fig = go.Figure()

# To make the dropdown work in offline HTML, we have to plot EVERY line for EVERY site first,
# but we set them to visible=False initially. The dropdown menu simply toggles visibility.

traces_per_site = 3 # We have 3 lines per site (VIIRS, Flared, Produced)

for site in unique_sites:
    site_data = df[df['EOG_Site_ID'] == site]
    
    # Trace 1: VIIRS Radiant Heat (Primary Y-Axis)
    fig.add_trace(go.Scatter(
        x=site_data['Date'], y=site_data['VIIRS_Radiant_Heat_Sum'],
        mode='lines+markers', name='VIIRS Heat (MW)',
        line=dict(color='#ff4500', width=2),
        visible=(site == unique_sites[0]) # Only the first site is visible by default
    ))
    
    # Trace 2: Reported Flared MCF (Secondary Y-Axis)
    fig.add_trace(go.Scatter(
        x=site_data['Date'], y=site_data['Reported_Flared_MCF'],
        mode='lines+markers', name='Reported Flared (MCF)',
        line=dict(color='#00f0ff', width=2, dash='dot'),
        yaxis='y2',
        visible=(site == unique_sites[0])
    ))
    
    # Trace 3: Reported Produced MCF (Secondary Y-Axis)
    fig.add_trace(go.Scatter(
        x=site_data['Date'], y=site_data['Reported_Produced_MCF'],
        mode='lines', name='Reported Production (MCF)',
        line=dict(color='#00ff66', width=2, dash='dash'),
        yaxis='y2',
        visible=(site == unique_sites[0])
    ))

# ==========================================
# 3. BUILD DROPDOWN MENU LOGIC
# ==========================================
dropdown_buttons = []

for i, site in enumerate(unique_sites):
    # Create a boolean array to turn ON the 3 traces for the selected site, and turn OFF all others
    visibility = [False] * (len(unique_sites) * traces_per_site)
    visibility[i*traces_per_site : (i+1)*traces_per_site] = [True, True, True]
    
    button = dict(
        label=f"EOG Site {site}",
        method="update",
        args=[{"visible": visibility},
              {"title": f"Temporal Audit Profile: EOG Site {site}"}]
    )
    dropdown_buttons.append(button)

# ==========================================
# 4. LAYOUT & STYLING
# ==========================================
fig.update_layout(
    title=f"Temporal Audit Profile: EOG Site {unique_sites[0]}",
    template="plotly_dark",
    updatemenus=[dict(
        active=0,
        buttons=dropdown_buttons,
        x=1.15, y=1.1, # Position dropdown top right
        xanchor="right", yanchor="top"
    )],
    xaxis=dict(title="Date"),
    yaxis=dict(
        title="VIIRS Radiant Heat (MW)",
        titlefont=dict(color="#ff4500"),
        tickfont=dict(color="#ff4500")
    ),
    yaxis2=dict(
        title="State Reported Volumes (MCF)",
        titlefont=dict(color="#00f0ff"),
        tickfont=dict(color="#00f0ff"),
        anchor="x",
        overlaying="y",
        side="right" # Put volume on the right side of the chart
    ),
    legend=dict(x=1.05, y=0.5), # Move legend out of the way
    hovermode="x unified" # Shows all three values at once when you hover over a date
)

# ==========================================
# 5. EXPORT
# ==========================================
output_html = os.path.join(viz_dir, 'interactive_timeseries_widget.html')
fig.write_html(output_html)

print("\n" + "="*60)
print(f"Interactive Time-Series Widget successfully generated!")
print(f"Open this file in Safari/Chrome: {output_html}")
print("="*60)