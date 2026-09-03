# Task List: Dashboard Redesign & Enhancements

- [x] Update `live_data.py`
  - [x] Add 48-hour recursive forecasting logic
  - [x] Update `get_city_history` to support multi-year same-day comparison
  - [x] Implement `get_all_cities_history` for multi-city same-day comparisons
- [x] Update `app.py`
  - [x] Add custom CSS theme (glassmorphic containers, Outfit font, clean margins)
  - [x] Redesign header and welcome card as a premium hero banner
  - [x] Format 5-city KPI row with color-coded status badges and hover animations
  - [x] Implement compact 2-column layout (Left: map + 48h bar chart; Right: health advisory)
  - [x] Move historical comparison charts to the bottom of the page in full-width, stacked layouts (not inside columns)
  - [x] Format Plotly charts to use transparent backgrounds and matching font/theme styling
  - [x] Add Satellite, Light Mode, and default Dark Mode layers to the Folium map with LayerControl switching
  - [x] Set default selected layer to Dark Mode explicitly using show=True/False flags
  - [x] Design Tab 2 (Model Insights & Explanations) with clean evaluation and SHAP image grids
- [x] Verification
  - [x] Verify layout responsiveness
  - [x] Verify images render correctly using absolute paths
  - [x] Verify multi-year same-day history comparisons function correctly on city selection
