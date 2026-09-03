import pathlib
import datetime
import pytz
import pandas as pd
import folium
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from streamlit_folium import st_folium
from live_data import (
    get_forecast, daqi_band, get_city_history, get_all_cities_history,
    DAQI_BANDS, CITIES, get_weather_forecast_detailed, predict_custom,
)
from PIL import Image

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="UK Air Quality Risk Forecast",
    page_icon="🌬",
    layout="wide",
)

ROOT = pathlib.Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Custom CSS for Premium Design & Fonts
# ---------------------------------------------------------------------------

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700;800&display=swap');
    
    /* Apply typography to the entire application */
    html, body, [class*="css"], .stApp {
        font-family: 'Outfit', sans-serif !important;
        background-color: #0e1117;
        color: #fafafa;
    }
    
    /* Remove streamlit padding */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 2rem !important;
    }
    
    /* Navigation / tab bar custom styles */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
        background-color: transparent;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
        padding-bottom: 5px;
    }
    
    .stTabs [data-baseweb="tab"] {
        font-family: 'Outfit', sans-serif !important;
        font-weight: 600 !important;
        font-size: 16px !important;
        color: #8892b0 !important;
        background: transparent !important;
        border: none !important;
        padding: 10px 16px !important;
        transition: all 0.3s ease !important;
    }
    
    .stTabs [aria-selected="true"] {
        color: #58a6ff !important;
        border-bottom: 2px solid #58a6ff !important;
    }
    
    /* Clean up the sidebar */
    [data-testid="stSidebar"] {
        background-color: #161b22 !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05);
    }
    
    /* Custom cards styling */
    .metric-card {
        background-color: #161b22;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(88, 166, 255, 0.2);
    }
    
    /* Live sensor pulse animation */
    @keyframes livepulse {
        0%, 100% { box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.5); }
        50%       { box-shadow: 0 0 0 5px rgba(46, 204, 113, 0); }
    }
    .pulse-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background-color: #2ECC71;
        border-radius: 50%;
        animation: livepulse 2s ease-in-out infinite;
        margin-right: 5px;
        vertical-align: middle;
    }
    .est-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        background-color: #F1C40F;
        border-radius: 50%;
        margin-right: 5px;
        vertical-align: middle;
    }
    
    /* Premium dark card */
    .premium-card {
        background-color: #0A0E17;
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.05);
        position: relative;
        overflow: hidden;
        display: flex;
        flex-direction: column;
        transition: transform 0.2s ease;
    }
    .premium-card:hover {
        transform: translateY(-2px);
    }
    
    /* Subtle top gradient glow based on DAQI color */
    .premium-card-bg {
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 200px;
        opacity: 0.2;
        z-index: 0;
    }

    /* Content wrapper to sit above background */
    .premium-card-content {
        position: relative;
        z-index: 1;
        padding: 18px 16px;
        display: flex;
        flex-direction: column;
        height: 100%;
    }

    /* Circular Gauge */
    .gauge-wrapper {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 30px 0;
    }
    
    .gauge-circle {
        width: 130px;
        height: 130px;
        border-radius: 50%;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        background: radial-gradient(circle at center, rgba(0,0,0,0.3) 0%, rgba(0,0,0,0.8) 100%);
        border: 4px solid; /* Color injected inline */
        box-shadow: inset 0px 0px 15px rgba(0,0,0,0.5); /* Inner shadow */
        position: relative;
    }
    
    /* Outer glow for the gauge */
    .gauge-glow {
        position: absolute;
        top: -4px; left: -4px; right: -4px; bottom: -4px;
        border-radius: 50%;
        z-index: -1;
        opacity: 0.5;
        filter: blur(8px);
    }
    
    .gauge-label {
        font-size: 11px;
        color: #a3acb9;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 2px;
    }
    
    .gauge-value {
        font-size: 38px;
        font-weight: 800;
        color: #ffffff;
        line-height: 1;
    }
    
    .gauge-unit {
        font-size: 13px;
        color: #8892b0;
        margin-top: 4px;
    }

    /* Decorative bottom line (mimicking sparkline) */
    .wave-bottom {
        height: 20px;
        width: 100%;
        margin-top: 15px;
        border-radius: 40%;
        opacity: 0.6;
        filter: blur(4px);
    }

    /* Hide Streamlit default components */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* ── Weather Strip ─────────────────────────────────────────── */
    .wx-strip {
        background: linear-gradient(135deg, #161b22 0%, #0d1117 100%);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 18px 24px;
        margin-top: 4px;
        margin-bottom: 8px;
    }
    .wx-city-label {
        font-size: 11px;
        font-weight: 700;
        color: #58a6ff;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 10px;
    }
    .wx-grid {
        display: grid;
        grid-template-columns: repeat(6, 1fr);
        gap: 8px;
    }
    .wx-item {
        background: rgba(255,255,255,0.03);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 10px;
        padding: 10px 8px;
        text-align: center;
        transition: background 0.2s ease, border-color 0.2s ease;
    }
    .wx-item:hover {
        background: rgba(88,166,255,0.07);
        border-color: rgba(88,166,255,0.25);
    }
    .wx-icon {
        font-size: 20px;
        line-height: 1;
        margin-bottom: 5px;
    }
    .wx-val {
        font-size: 16px;
        font-weight: 700;
        color: #fafafa;
        line-height: 1.1;
    }
    .wx-unit {
        font-size: 10px;
        color: #8892b0;
        margin-top: 2px;
    }
    .wx-lbl {
        font-size: 9px;
        color: #636d7e;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-top: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# DAQI guidance text
# ---------------------------------------------------------------------------

DAQI_ADVICE = {
    "Low": {
        "colour": "#2ECC71",
        "bg_alpha": "rgba(46, 204, 113, 0.15)",
        "advice": (
            "Air quality is good. No action needed. "
            "Suitable for all outdoor activities."
        ),
        "emoji": "🟢"
    },
    "Moderate": {
        "colour": "#F1C40F",
        "bg_alpha": "rgba(241, 196, 15, 0.15)",
        "advice": (
            "Air quality is acceptable. Adults and children with lung or heart conditions "
            "should consider reducing prolonged strenuous outdoor activity."
        ),
        "emoji": "🟡"
    },
    "High": {
        "colour": "#E67E22",
        "bg_alpha": "rgba(230, 126, 34, 0.15)",
        "advice": (
            "Everyone may begin to experience health effects. "
            "People with heart or lung disease, older adults, and children should "
            "reduce prolonged or heavy outdoor activity."
        ),
        "emoji": "🟠"
    },
    "Very High": {
        "colour": "#E74C3C",
        "bg_alpha": "rgba(231, 76, 60, 0.15)",
        "advice": (
            "Health alert: everyone may experience more serious health effects. "
            "Everyone should avoid prolonged or heavy outdoor exertion."
        ),
        "emoji": "🔴"
    },
}

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(ttl=1800)
def load_forecast() -> pd.DataFrame:
    return get_forecast()

with st.spinner("Fetching live readings and running forecast..."):
    df = load_forecast()

# ---------------------------------------------------------------------------
# Sidebar (Controls & About)
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("<h2 style='margin-top:0;'>⚙️ Controls</h2>", unsafe_allow_html=True)
    if st.button("Refresh Live Data 🔄", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    st.subheader("Data Freshness")
    last_updated = pd.to_datetime(df['last_updated'].iloc[0])
    now = pd.Timestamp.utcnow()
    mins_ago = (now - last_updated).total_seconds() / 60
    if mins_ago < 30:
        st.success(f"🟢 Fresh (Updated {int(mins_ago)}m ago)")
    elif mins_ago < 60:
        st.warning(f"🟡 Good (Updated {int(mins_ago)}m ago)")
    else:
        st.error(f"🔴 Stale (Updated {int(mins_ago)}m ago)")

    st.markdown("---")
    with st.expander("ℹ️ Navigation Guide", expanded=False):
        st.markdown("""
        * **Metric Cards**: Hover to highlight; color-coded by current DAQI.
        * **Risk Map**: Zoom and click pins to see local pollutant levels.
        * **Comparative Chart**: Compare 24h vs 48h forecasts.
        * **Model Insights**: See exact SHAP plots and accuracy metrics in Tab 2.
        """)

    st.markdown("---")
    st.markdown(
        """
        <div style="font-size:12px; color:#8892b0;">
            <b>Stanley Amankonah Agyei</b><br>
            MSc Data Science Dissertation<br>
            University of Sunderland<br><br>
            <b>Model:</b> XGBoost (RMSE 5.14 µg/m³)<br>
            <b>Ingestion:</b> DEFRA AURN + OpenAQ
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------------------------------------------------
# Main Page Layout (Tabs)
# ---------------------------------------------------------------------------

tab_live, tab_predictor = st.tabs([
    "🌍 Live Forecast Dashboard",
    "🔮 Custom Air Quality Predictor",
])

with tab_live:
    # ---------------------------------------------------------------------------
    # Hero Header Banner
    # ---------------------------------------------------------------------------
    st.markdown("""<div style="background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); padding: 30px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 25px;">
<h1 style="margin: 0; color: #fafafa; font-size: 32px; font-weight: 800;">🌬️ UK Air Quality Risk Forecast</h1>
<p style="margin: 10px 0 0 0; color: #8892b0; font-size: 16px; font-weight: 400;">
Live real-time PM2.5 monitoring and 24-48 hour XGBoost machine learning predictions for UK metropolitan centers.
</p>
</div>""", unsafe_allow_html=True)

    # ---------------------------------------------------------------------------
    # Live Air Quality Bulletin — dynamic AI-style news feed
    # ---------------------------------------------------------------------------

    # ── Generate insights from the live df ────────────────────────────────────
    def _generate_bulletin(df: pd.DataFrame) -> list[dict]:
        """
        Auto-generate a list of insight dicts from the live forecast DataFrame.
        Each dict: {icon, title, text, colour}
        """
        insights = []
        now_uk = datetime.datetime.now(pytz.timezone("Europe/London"))
        hour   = now_uk.hour

        df = df.copy()
        df["delta_24"] = df["pm25_forecast_24h"] - df["pm25_current"]
        df["delta_48"] = df["pm25_forecast_48h"] - df["pm25_current"]

        bands_now = df["daqi_current"].tolist()
        all_low   = all(b == "Low" for b in bands_now)
        any_high  = any(b in ("High", "Very High") for b in bands_now)

        # ── 1. Overall status headline ──────────────────────────────────────
        if all_low:
            insights.append({
                "icon": "🟢", "title": "All Cities: Clear",
                "text": (
                    "All 5 monitored UK cities are currently showing <b>Low</b> DAQI — "
                    "air quality is good and safe for outdoor activities across the board."
                ),
                "colour": "#2ECC71",
            })
        elif any_high:
            high_cities = [r["city_short"] for _, r in df.iterrows() if r["daqi_current"] in ("High","Very High")]
            insights.append({
                "icon": "🔴", "title": "Elevated Risk Detected",
                "text": (
                    f"<b>{', '.join(high_cities)}</b> {'is' if len(high_cities)==1 else 'are'} currently "
                    f"in the <b>High or Very High</b> DAQI band — sensitive groups should avoid prolonged outdoor exertion."
                ),
                "colour": "#E74C3C",
            })
        else:
            mod_cities = [r["city_short"] for _, r in df.iterrows() if r["daqi_current"] == "Moderate"]
            if mod_cities:
                insights.append({
                    "icon": "🟡", "title": "Moderate Conditions",
                    "text": (
                        f"<b>{', '.join(mod_cities)}</b> {'is' if len(mod_cities)==1 else 'are'} currently "
                        "at <b>Moderate</b> DAQI. Asthmatics, elderly and children should consider reducing "
                        "strenuous outdoor activity."
                    ),
                    "colour": "#F1C40F",
                })

        # ── 2. Cleanest city ────────────────────────────────────────────────
        best = df.loc[df["pm25_current"].idxmin()]
        insights.append({
            "icon": "🏆", "title": "Cleanest Air Right Now",
            "text": (
                f"<b>{best['city_short']}</b> has the lowest PM2.5 reading at "
                f"<b>{best['pm25_current']} µg/m³</b> — well within safe limits."
            ),
            "colour": "#2ECC71",
        })

        # ── 3. Most polluted city ───────────────────────────────────────────
        worst = df.loc[df["pm25_current"].idxmax()]
        if worst["pm25_current"] > best["pm25_current"] + 3:   # Only if meaningful gap
            insights.append({
                "icon": "📍", "title": "Highest Concentration",
                "text": (
                    f"<b>{worst['city_short']}</b> has the highest current PM2.5 at "
                    f"<b>{worst['pm25_current']} µg/m³</b> "
                    f"— DAQI: {worst['daqi_current']}."
                ),
                "colour": DAQI_ADVICE[worst["daqi_current"]]["colour"],
            })

        # ── 4. Cities above WHO guideline ───────────────────────────────────
        WHO = 15.0
        above = df[df["pm25_current"] > WHO]
        if not above.empty:
            names = ", ".join(above["city_short"].tolist())
            insights.append({
                "icon": "⚠️", "title": "Above WHO Guideline",
                "text": (
                    f"<b>{names}</b> {'is' if len(above)==1 else 'are'} currently above the "
                    f"WHO annual mean guideline of <b>15 µg/m³</b>. The WHO sets this as the safe "
                    "long-term exposure threshold."
                ),
                "colour": "#E67E22",
            })
        else:
            insights.append({
                "icon": "✅", "title": "WHO Guideline Met",
                "text": (
                    "All cities are currently <b>below the WHO annual mean guideline</b> of 15 µg/m³. "
                    "Today's air quality poses minimal long-term health risk."
                ),
                "colour": "#2ECC71",
            })

        # ── 5. Biggest 24h rise ─────────────────────────────────────────────
        rising = df.loc[df["delta_24"].idxmax()]
        if rising["delta_24"] > 2.0:
            pct = round(rising["delta_24"] / max(rising["pm25_current"], 0.1) * 100)
            insights.append({
                "icon": "📈", "title": "Rising Trend — 24h Alert",
                "text": (
                    f"The model forecasts PM2.5 in <b>{rising['city_short']}</b> to rise by "
                    f"<b>{rising['delta_24']:.1f} µg/m³ (+{pct}%)</b> over the next 24 hours — "
                    f"reaching {rising['pm25_forecast_24h']} µg/m³ ({rising['daqi_forecast']})."
                ),
                "colour": "#F1C40F",
            })

        # ── 6. Biggest 24h improvement ──────────────────────────────────────
        falling = df.loc[df["delta_24"].idxmin()]
        if falling["delta_24"] < -2.0:
            insights.append({
                "icon": "📉", "title": "Improving — Good News",
                "text": (
                    f"Air quality in <b>{falling['city_short']}</b> is forecast to improve by "
                    f"<b>{abs(falling['delta_24']):.1f} µg/m³</b> over the next 24 hours — "
                    f"dropping to {falling['pm25_forecast_24h']} µg/m³ ({falling['daqi_forecast']})."
                ),
                "colour": "#2ECC71",
            })

        # ── 7. DAQI band changes forecast ───────────────────────────────────
        for _, row in df.iterrows():
            curr, fore = row["daqi_current"], row["daqi_forecast"]
            city = row["city_short"]
            band_order = {"Low": 0, "Moderate": 1, "High": 2, "Very High": 3}
            if band_order.get(fore, 0) > band_order.get(curr, 0):
                insights.append({
                    "icon": "⚡", "title": f"{city}: Band Worsening",
                    "text": (
                        f"<b>{city}</b> is forecast to move from <b>{curr}</b> → <b>{fore}</b> "
                        f"in 24 hours. Sensitive groups in {city} should plan outdoor activities for today."
                    ),
                    "colour": DAQI_ADVICE[fore]["colour"],
                })
                break  # Only show the first band-worsening event to keep it concise

        # ── 8. Time-of-day context ──────────────────────────────────────────
        if 7 <= hour <= 9:
            insights.append({
                "icon": "🚗", "title": "Morning Rush Hour",
                "text": (
                    "PM2.5 typically peaks during morning rush hours (7–9 AM) due to traffic emissions. "
                    "Current readings reflect this pattern — levels may ease by mid-morning."
                ),
                "colour": "#8892b0",
            })
        elif 16 <= hour <= 19:
            insights.append({
                "icon": "🌆", "title": "Evening Rush Hour",
                "text": (
                    "Evening commuter traffic (4–7 PM) typically causes a secondary PM2.5 peak. "
                    "Check back in 2–3 hours for updated readings as conditions evolve."
                ),
                "colour": "#8892b0",
            })
        elif 22 <= hour or hour <= 5:
            insights.append({
                "icon": "🌙", "title": "Night-time Readings",
                "text": (
                    "Overnight PM2.5 is typically lower due to reduced traffic, but atmospheric "
                    "temperature inversions can trap particulates — watch for elevated readings at dawn."
                ),
                "colour": "#58a6ff",
            })

        return insights[:6]   # Cap at 6 cards to keep the layout clean

    bulletin    = _generate_bulletin(df)
    now_uk_str  = datetime.datetime.now(pytz.timezone("Europe/London")).strftime("%A %d %B · %H:%M BST")

    # ── Build slide HTML from bulletin items ───────────────────────────────────
    slides_html = ""
    for i, item in enumerate(bulletin):
        active_cls = " active" if i == 0 else ""
        slides_html += f"""
        <div class="slide{active_cls}" style="border-left: 4px solid {item['colour']};">
          <div class="slide-icon">{item['icon']}</div>
          <div class="slide-content">
            <div class="slide-category" style="color:{item['colour']};">{item['title']}</div>
            <div class="slide-text">{item['text']}</div>
          </div>
          <div class="slide-num-badge" style="background:{item['colour']}22;
               border:1px solid {item['colour']}44; color:{item['colour']};">
            {i+1}/{len(bulletin)}
          </div>
        </div>"""

    carousel_html = f"""<!DOCTYPE html>
<html>
<head>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ background:transparent; font-family:'Outfit','Segoe UI',sans-serif; overflow:hidden; }}

  .bulletin-wrap {{
    width:100%; background:linear-gradient(135deg,#161b22 0%,#0d1117 100%);
    border-radius:14px; border:1px solid rgba(255,255,255,0.07); overflow:hidden;
  }}

  /* ── Header ── */
  .bul-header {{
    display:flex; justify-content:space-between; align-items:center;
    padding:13px 22px 11px; border-bottom:1px solid rgba(255,255,255,0.05);
  }}
  .bul-title {{ font-size:13px; font-weight:700; color:#fafafa; letter-spacing:.3px; }}
  .live-badge {{ display:flex; align-items:center; gap:6px; font-size:11px; color:#636d7e; }}
  .pdot {{ width:7px;height:7px;border-radius:50%;background:#2ECC71;
           animation:pd 2s ease-in-out infinite; }}
  @keyframes pd {{ 0%,100%{{opacity:1}}50%{{opacity:.35}} }}

  /* ── Progress bar ── */
  .prog-bar {{ height:2px; background:rgba(255,255,255,0.05); }}
  .prog-fill {{ height:100%; background:#58a6ff; width:0%; }}

  /* ── Slides ── */
  .slides-wrap {{ position:relative; height:130px; overflow:hidden; }}

  .slide {{
    position:absolute; inset:0; padding:0 28px;
    display:flex; align-items:center; gap:22px;
    opacity:0; transform:translateX(50px);
    transition:opacity .45s ease, transform .45s cubic-bezier(.4,0,.2,1);
    pointer-events:none;
  }}
  .slide.active {{ opacity:1; transform:translateX(0); pointer-events:auto; }}
  .slide.exit   {{ opacity:0; transform:translateX(-50px); }}

  .slide-icon {{ font-size:52px; line-height:1; flex-shrink:0; }}
  .slide-content {{ flex:1; }}
  .slide-category {{
    font-size:11px; font-weight:700; text-transform:uppercase;
    letter-spacing:1.1px; margin-bottom:7px;
  }}
  .slide-text {{
    font-size:15px; color:#c0cad9; line-height:1.65; font-weight:400;
  }}
  .slide-text b {{ color:#fafafa; font-weight:700; }}

  .slide-num-badge {{
    flex-shrink:0; font-size:11px; font-weight:700;
    padding:4px 10px; border-radius:20px; letter-spacing:.5px;
  }}

  /* ── Footer ── */
  .bul-footer {{
    display:flex; justify-content:space-between; align-items:center;
    padding:9px 22px 12px; border-top:1px solid rgba(255,255,255,0.05);
  }}
  .dots {{ display:flex; gap:6px; align-items:center; }}
  .dot {{
    width:6px;height:6px;border-radius:50%;background:rgba(255,255,255,0.15);
    cursor:pointer;transition:all .3s;
  }}
  .dot.active {{ background:#58a6ff; width:20px; border-radius:3px; }}

  .nav-btns {{ display:flex; gap:8px; }}
  .nav-btn {{
    width:30px;height:30px;border-radius:50%;border:1px solid rgba(255,255,255,0.1);
    background:rgba(255,255,255,0.05);color:#8892b0;cursor:pointer;
    display:flex;align-items:center;justify-content:center;font-size:16px;
    transition:all .2s; user-select:none;
  }}
  .nav-btn:hover {{ background:rgba(88,166,255,0.15);color:#58a6ff;border-color:rgba(88,166,255,.35); }}
</style>
</head>
<body>
<div class="bulletin-wrap">
  <div class="bul-header">
    <div class="bul-title">📰 Live Air Quality Bulletin</div>
    <div class="live-badge">
      <div class="pdot"></div>
    &nbsp;·&nbsp; {now_uk_str}
    </div>
  </div>

  <div class="prog-bar"><div class="prog-fill" id="prog"></div></div>

  <div class="slides-wrap" id="sw">
    {slides_html}
  </div>

  <div class="bul-footer">
    <div class="dots" id="dots"></div>
    <div class="nav-btns">
      <div class="nav-btn" id="prev">&#8249;</div>
      <div class="nav-btn" id="next">&#8250;</div>
    </div>
  </div>
</div>

<script>
  const slides  = document.querySelectorAll('.slide');
  const dotsEl  = document.getElementById('dots');
  const prog    = document.getElementById('prog');
  const DUR     = 5000;
  let cur = 0, timer = null;

  // Build dots
  slides.forEach((_, i) => {{
    const d = document.createElement('div');
    d.className = 'dot' + (i === 0 ? ' active' : '');
    d.addEventListener('click', () => goTo(i, true));
    dotsEl.appendChild(d);
  }});

  function goTo(n, manual) {{
    slides[cur].classList.remove('active');
    slides[cur].classList.add('exit');
    const prev = cur;
    cur = ((n % slides.length) + slides.length) % slides.length;
    setTimeout(() => slides[prev].classList.remove('exit'), 500);
    slides[cur].classList.add('active');
    dotsEl.querySelectorAll('.dot').forEach((d,i) => d.classList.toggle('active', i===cur));
    startProgress();
  }}

  function startProgress() {{
    clearTimeout(timer);
    prog.style.transition = 'none';
    prog.style.width = '0%';
    requestAnimationFrame(() => requestAnimationFrame(() => {{
      prog.style.transition = `width ${{DUR}}ms linear`;
      prog.style.width = '100%';
    }}));
    timer = setTimeout(() => goTo(cur + 1), DUR);
  }}

  document.getElementById('next').addEventListener('click', () => goTo(cur + 1, true));
  document.getElementById('prev').addEventListener('click', () => goTo(cur - 1, true));

  startProgress();
</script>
</body>
</html>"""

    import streamlit.components.v1 as _components
    _components.html(carousel_html, height=210, scrolling=False)

    st.markdown("<div style='margin-bottom:12px;'></div>", unsafe_allow_html=True)


    # ---------------------------------------------------------------------------
    # Unified City Cards — Live Reading + Forecasts in one card
    # ---------------------------------------------------------------------------
    city_cols = st.columns(5)
    for col, row in zip(city_cols, df.itertuples(index=False)):
        # Data freshness
        ts_raw = getattr(row, 'reading_timestamp', '')
        is_live = getattr(row, 'data_source', '') == "OpenAQ (Live Sensor)"
        station_label = getattr(row, 'live_station_name', row.station)

        if ts_raw:
            try:
                ts_dt = pd.to_datetime(ts_raw, utc=True)
                ts_display = ts_dt.strftime("%H:%M UTC")
            except Exception:
                ts_display = "Recent"
        else:
            ts_display = "Estimated"

        # Forecast delta vs current
        delta_24 = round(row.pm25_forecast_24h - row.pm25_current, 1)
        arrow_24 = "↑" if delta_24 > 0 else "↓"
        arrow_col_24 = "#E74C3C" if delta_24 > 0 else "#2ECC71"

        delta_48 = round(row.pm25_forecast_48h - row.pm25_current, 1)
        arrow_48 = "↑" if delta_48 > 0 else "↓"
        arrow_col_48 = "#E74C3C" if delta_48 > 0 else "#2ECC71"

        advice = DAQI_ADVICE[row.daqi_current]
        dot_html = '<span class="pulse-dot"></span>' if is_live else '<span class="est-dot"></span>'
        source_label = "Live sensor" if is_live else "Estimated"
        source_color = "#2ECC71" if is_live else "#F1C40F"

        with col:
            st.markdown(f"""<div class="premium-card">
<div class="premium-card-bg" style="background: radial-gradient(circle at top, {advice['colour']} 0%, transparent 70%);"></div>
<div class="premium-card-content">
<div style="display:flex; justify-content:space-between; align-items:center;">
<div style="display:flex; align-items:center; gap:8px;">
<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="{advice['colour']}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 22h16"/><path d="M12 2v20"/><path d="M8 22V10l4-2 4 2v12"/><path d="M4 22V14l4-2"/><path d="M20 22V14l-4-2"/></svg>
<span style="font-size:16px; font-weight:700; color:#fafafa; letter-spacing:0.3px;">{row.city_short}</span>
</div>
<span style="font-size:10px; font-weight:700; color:{advice['colour']}; background:{advice['bg_alpha']}; border: 1px solid {advice['colour']}40; padding:3px 8px; border-radius:12px; text-transform:uppercase;">{row.daqi_current}</span>
</div>
<div style="font-size:10px; color:#a3acb9; margin-top:8px; display:flex; align-items:center;">
{dot_html}<span style="color:{source_color}; font-weight:600;">{source_label}</span>&nbsp;&middot;&nbsp;{ts_display}
</div>
<div class="gauge-wrapper">
<div class="gauge-circle" style="border-color: {advice['colour']};">
<div class="gauge-glow" style="background: {advice['colour']};"></div>
<div class="gauge-label">Now</div>
<div class="gauge-value">{row.pm25_current}</div>
<div class="gauge-unit">µg/m³</div>
</div>
</div>
<div style="display:flex; justify-content:space-between; margin-top:auto; padding-top:15px; border-top:1px solid rgba(255,255,255,0.05);">
<div style="flex:1; text-align:center;">
<div style="font-size:9px; color:#a3acb9; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">+24h Forecast</div>
<div style="font-size:16px; font-weight:700; color:#fafafa;">{row.pm25_forecast_24h}</div>
<div style="font-size:11px; font-weight:600; color:{arrow_col_24}; margin-top:2px;">{arrow_24} {abs(delta_24)} µg/m³</div>
</div>
<div style="width:1px; background:rgba(255,255,255,0.08); margin:0 10px;"></div>
<div style="flex:1; text-align:center;">
<div style="font-size:9px; color:#a3acb9; text-transform:uppercase; letter-spacing:0.5px; margin-bottom:4px;">+48h Forecast</div>
<div style="font-size:16px; font-weight:700; color:#fafafa;">{row.pm25_forecast_48h}</div>
<div style="font-size:11px; font-weight:600; color:{arrow_col_48}; margin-top:2px;">{arrow_48} {abs(delta_48)} µg/m³</div>
</div>
</div>
<div class="wave-bottom" style="background: radial-gradient(ellipse at center, {advice['colour']}40 0%, transparent 70%);"></div>
</div>
</div>""", unsafe_allow_html=True)


    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------------------------
    # Rich Weather Forecast Widget (Open-Meteo — no model, pure API data)
    # ---------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("<h3 style='margin-bottom:4px;'>🌤️ Local Weather Forecast</h3>", unsafe_allow_html=True)
    st.caption("Real-time hourly + 7-day forecast powered by Open-Meteo")

    # ── WMO weather-code helpers ────────────────────────────────────────────────
    WMO_EMOJI = {
        0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
        45: "🌫️", 48: "🌫️",
        51: "🌦️", 53: "🌦️", 55: "🌧️",
        61: "🌧️", 63: "🌧️", 65: "🌧️",
        71: "🌨️", 73: "🌨️", 75: "🌨️", 77: "🌨️",
        80: "🌦️", 81: "🌦️", 82: "⛈️",
        85: "🌨️", 86: "🌨️",
        95: "⛈️", 96: "⛈️", 99: "⛈️",
    }
    WMO_DESC = {
        0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
        45: "Fog", 48: "Icy fog",
        51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
        61: "Light rain", 63: "Rain", 65: "Heavy rain",
        71: "Light snow", 73: "Snow", 75: "Heavy snow", 77: "Snow grains",
        80: "Light showers", 81: "Showers", 82: "Heavy showers",
        85: "Light snow showers", 86: "Snow showers",
        95: "Thunderstorm", 96: "Thunderstorm + hail", 99: "Thunderstorm + hail",
    }
    DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    def _wmo_emoji(code):
        return WMO_EMOJI.get(int(code) if code is not None else 0, "🌡️")

    def _wmo_desc(code):
        return WMO_DESC.get(int(code) if code is not None else 0, "Unknown")

    def _compass(deg):
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        return dirs[round(float(deg) / 45) % 8]

    # ── City selector ───────────────────────────────────────────────────────────
    wx_city = st.selectbox(
        "Select city for weather detail:",
        [c["short"] for c in CITIES],
        key="wx_city_sel",
    )
    wx_city_info = next(c for c in CITIES if c["short"] == wx_city)

    @st.cache_data(ttl=1800)
    def load_wx_detail(lat, lon):
        return get_weather_forecast_detailed(lat, lon)

    wx = load_wx_detail(wx_city_info["lat"], wx_city_info["lon"])
    hourly = wx.get("hourly", {})
    daily  = wx.get("daily", {})
    current = wx.get("current", {})

    if not hourly or not daily:
        st.warning("⚠️ Weather data unavailable. Try refreshing.")
    else:
        import datetime as dt

        now_local = dt.datetime.now()
        today_label = now_local.strftime("%A %d %B")

        # ── Slice next 24 hours from hourly arrays ──────────────────────────────
        all_times = hourly.get("time", [])
        now_str   = now_local.strftime("%Y-%m-%dT%H:00")
        try:
            start_idx = all_times.index(now_str)
        except ValueError:
            start_idx = 0
        end_idx = min(start_idx + 25, len(all_times))

        h_times  = all_times[start_idx:end_idx]
        h_temp   = hourly.get("temperature_2m", [])[start_idx:end_idx]
        h_precip = hourly.get("precipitation", [])[start_idx:end_idx]
        h_precip_prob = hourly.get("precipitation_probability", [])[start_idx:end_idx]
        h_wind   = hourly.get("wind_speed_10m", [])[start_idx:end_idx]
        h_wdir   = hourly.get("wind_direction_10m", [])[start_idx:end_idx]
        h_hum    = hourly.get("relative_humidity_2m", [])[start_idx:end_idx]
        h_code   = hourly.get("weather_code", [])[start_idx:end_idx]

        h_labels = [t[11:16] for t in h_times]  # "HH:MM"

        # Current values
        cur_temp  = current.get("temperature_2m", h_temp[0] if h_temp else 0)
        cur_code  = current.get("weather_code", h_code[0] if h_code else 0)
        cur_hum   = current.get("relative_humidity_2m", h_hum[0] if h_hum else 0)
        cur_wind  = current.get("wind_speed_10m", h_wind[0] if h_wind else 0)
        temp_max  = daily.get("temperature_2m_max", [cur_temp])[0]
        temp_min  = daily.get("temperature_2m_min", [cur_temp])[0]
        avg_hum   = round(sum(h_hum) / len(h_hum), 0) if h_hum else cur_hum

        # ── TOP ROW: main panel (left) + 2 charts stacked (right) ──────────────
        col_main, col_charts = st.columns([2.2, 1])

        with col_main:
            # ── Header ───────────────────────────────────────────────────────
            st.markdown(f"""
<div style="background:linear-gradient(135deg,#161b22 0%,#0d1117 100%);
            border:1px solid rgba(255,255,255,0.07); border-radius:14px;
            padding:20px 24px 16px 24px; margin-bottom:10px;">
  <div style="font-size:13px; color:#8892b0; margin-bottom:4px;">{today_label}</div>
  <div style="display:flex; align-items:center; gap:16px; margin-bottom:4px;">
    <span style="font-size:48px; font-weight:800; color:#fafafa; line-height:1;">
        {round(temp_max)}°/<span style="color:#8892b0; font-size:34px;">{round(temp_min)}°</span>
    </span>
    <span style="font-size:50px; line-height:1;">{_wmo_emoji(cur_code)}</span>
    <span style="font-size:16px; color:#a3acb9; margin-left:auto;">{_wmo_desc(cur_code)}</span>
  </div>
  <div style="display:flex; gap:18px; font-size:12px; color:#636d7e;">
    <span>💧 Humidity {int(cur_hum)}%</span>
    <span>🌬️ Wind {round(cur_wind)} km/h</span>
  </div>
</div>
""", unsafe_allow_html=True)

            # ── Hourly temperature + icon strip ──────────────────────────────
            strip_cells = ""
            for i, (lbl, tmp, code, prob) in enumerate(zip(h_labels, h_temp, h_code, h_precip_prob)):
                prob_html = (
                    f'<div style="font-size:9px;color:#58a6ff;">{int(prob)}%</div>'
                    if prob and float(prob) >= 10 else
                    '<div style="font-size:9px;color:transparent;">·</div>'
                )
                is_now = (i == 0)
                bg = "rgba(88,166,255,0.12)" if is_now else "rgba(255,255,255,0.02)"
                border = "1px solid rgba(88,166,255,0.4)" if is_now else "1px solid rgba(255,255,255,0.05)"
                strip_cells += f"""
<div style="flex:0 0 auto; width:64px; text-align:center; background:{bg};
            border:{border}; border-radius:10px; padding:8px 4px; margin-right:6px;">
  <div style="font-size:11px; color:#8892b0; margin-bottom:4px;">
      {"Now" if is_now else lbl}</div>
  <div style="font-size:22px; line-height:1; margin-bottom:4px;">{_wmo_emoji(code)}</div>
  {prob_html}
  <div style="font-size:13px; font-weight:700; color:#fafafa; margin-top:4px;">{round(float(tmp))}°</div>
</div>"""

            st.markdown(f"""
<div style="background:#0d1117; border:1px solid rgba(255,255,255,0.06); border-radius:12px;
            padding:12px 14px; overflow-x:auto;">
  <div style="display:flex; align-items:flex-end; padding-bottom:4px; min-width:max-content;">
    {strip_cells}
  </div>
</div>
""", unsafe_allow_html=True)

        with col_charts:
            # ── Precipitation chart ───────────────────────────────────────────
            st.markdown("""<div style="font-size:12px; color:#a3acb9; font-weight:600;
                                       margin-bottom:4px;">🌧️ Precipitation (mm)</div>""",
                        unsafe_allow_html=True)
            fig_rain = go.Figure()
            fig_rain.add_trace(go.Bar(
                x=h_labels[:13], y=h_precip[:13],
                marker_color="#58a6ff",
                marker_line_width=0,
                name="Rain mm",
            ))
            fig_rain.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(13,17,23,0.95)",
                margin=dict(l=0, r=0, t=4, b=0), height=130,
                showlegend=False,
                font=dict(family="Outfit", size=10, color="#8892b0"),
                xaxis=dict(showgrid=False, color="#636d7e", tickfont_size=9),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                           color="#636d7e", tickfont_size=9, nticks=3),
            )
            st.plotly_chart(fig_rain, use_container_width=True, key="wx_rain")

            # ── Wind chart ────────────────────────────────────────────────────
            st.markdown("""<div style="font-size:12px; color:#a3acb9; font-weight:600;
                                       margin-bottom:4px;">🌬️ Wind Speed (km/h)</div>""",
                        unsafe_allow_html=True)
            fig_wind = go.Figure()
            fig_wind.add_trace(go.Scatter(
                x=h_labels[:13], y=h_wind[:13],
                mode="lines+markers",
                line=dict(color="#58a6ff", width=2, shape="spline"),
                marker=dict(color="#58a6ff", size=5),
                fill="tozeroy",
                fillcolor="rgba(88,166,255,0.08)",
                name="Wind km/h",
            ))
            # Wind direction annotations (every 3rd hour)
            for i in range(0, min(13, len(h_labels)), 3):
                deg = h_wdir[i] if i < len(h_wdir) else 0
                compass = _compass(deg)
                fig_wind.add_annotation(
                    x=h_labels[i], y=h_wind[i] if i < len(h_wind) else 0,
                    text=f"<b>{compass}</b>",
                    showarrow=False,
                    yshift=14,
                    font=dict(size=9, color="#58a6ff"),
                )
            fig_wind.update_layout(
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(13,17,23,0.95)",
                margin=dict(l=0, r=0, t=4, b=0), height=130,
                showlegend=False,
                font=dict(family="Outfit", size=10, color="#8892b0"),
                xaxis=dict(showgrid=False, color="#636d7e", tickfont_size=9),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)",
                           color="#636d7e", tickfont_size=9, nticks=3),
            )
            st.plotly_chart(fig_wind, use_container_width=True, key="wx_wind")

        # ── Humidity full-width chart ───────────────────────────────────────────
        st.markdown(f"""<div style="font-size:12px; color:#a3acb9; font-weight:600;
                         margin-bottom:4px; margin-top:4px;">
            💧 Humidity — Day average <b style="color:#fafafa;">{int(avg_hum)}%</b>
        </div>""", unsafe_allow_html=True)
        fig_hum = go.Figure()
        fig_hum.add_trace(go.Scatter(
            x=h_labels, y=h_hum,
            mode="lines",
            line=dict(color="rgba(88,166,255,0.9)", width=2, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(88,166,255,0.07)",
            name="Humidity %",
        ))
        fig_hum.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(13,17,23,0.95)",
            margin=dict(l=0, r=0, t=4, b=0), height=110,
            showlegend=False,
            font=dict(family="Outfit", size=10, color="#8892b0"),
            xaxis=dict(showgrid=False, color="#636d7e", tickfont_size=9),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.04)",
                       color="#636d7e", tickfont_size=9, range=[0, 100], nticks=3),
        )
        st.plotly_chart(fig_hum, use_container_width=True, key="wx_hum")

        # ── 7-Day Daily Forecast ────────────────────────────────────────────────
        st.markdown("""<div style="font-size:12px; color:#a3acb9; font-weight:600;
                         margin-bottom:6px;">📅 7-Day Forecast</div>""",
                    unsafe_allow_html=True)

        d_dates  = daily.get("time", [])[:8]
        d_codes  = daily.get("weather_code", [])[:8]
        d_maxs   = daily.get("temperature_2m_max", [])[:8]
        d_mins   = daily.get("temperature_2m_min", [])[:8]
        d_precip = daily.get("precipitation_sum", [])[:8]
        d_wind   = daily.get("wind_speed_10m_max", [])[:8]

        day_cols = st.columns(len(d_dates))
        today_date_str = now_local.strftime("%Y-%m-%d")
        for ci, (col_d, ddate, dcode, dmax, dmin, dprecip, dwind_max) in enumerate(
            zip(day_cols, d_dates, d_codes, d_maxs, d_mins, d_precip, d_wind)
        ):
            is_today = (ddate == today_date_str)
            try:
                dt_obj  = dt.datetime.strptime(ddate, "%Y-%m-%d")
                day_lbl = "Today" if is_today else DAY_NAMES[dt_obj.weekday()]
                date_lbl = dt_obj.strftime("%d %b")
            except Exception:
                day_lbl = ddate; date_lbl = ""

            bg_style = (
                "background:rgba(88,166,255,0.12); border:1px solid rgba(88,166,255,0.35);"
                if is_today else
                "background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06);"
            )
            rain_txt = f"🌧️ {round(float(dprecip), 1)}mm" if dprecip and float(dprecip) > 0 else "☀️ Dry"
            with col_d:
                st.markdown(f"""
<div style="{bg_style} border-radius:12px; padding:12px 6px; text-align:center;">
  <div style="font-size:11px; font-weight:700; color:{'#58a6ff' if is_today else '#a3acb9'};
               margin-bottom:2px;">{day_lbl}</div>
  <div style="font-size:10px; color:#636d7e; margin-bottom:8px;">{date_lbl}</div>
  <div style="font-size:30px; line-height:1; margin-bottom:8px;">{_wmo_emoji(dcode)}</div>
  <div style="font-size:13px; font-weight:700; color:#fafafa;">{round(float(dmax))}°</div>
  <div style="font-size:11px; color:#636d7e; margin-bottom:6px;">{round(float(dmin))}°</div>
  <div style="font-size:9px; color:#8892b0;">{rain_txt}</div>
  <div style="font-size:9px; color:#8892b0; margin-top:2px;">💨 {round(float(dwind_max))} km/h</div>
</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ---------------------------------------------------------------------------
    # Two-Column Layout (Left: Map & Bar Chart, Right: Advice & Same-Day History)
    # ---------------------------------------------------------------------------
    col_left, col_right = st.columns([1.6, 1])

    with col_left:
        # Map Container
        st.markdown("<h3 style='margin-bottom:5px;'>🗺️ Live UK Risk Map</h3>", unsafe_allow_html=True)
        st.caption("Circles represent monitoring stations, sized by current PM2.5 levels.")
        
        # Inline Legend
        legend_html = "<div style='margin-bottom:15px; font-size:12px; color:#8892b0;'>"
        for band, info in DAQI_ADVICE.items():
            legend_html += f"<span style='display:inline-block; margin-right:15px;'><span style='color:{info['colour']}; font-weight:bold;'>{info['emoji']} {band}</span></span>"
        legend_html += "</div>"
        st.markdown(legend_html, unsafe_allow_html=True)
        
        m = folium.Map(location=[54.5, -2.5], zoom_start=5.6, tiles=None)
        
        # Base layers, all via Esri's free, no-API-key-required REST tile services.
        # (folium's "CartoDB dark_matter"/"CartoDB positron" aliases now require a CARTO API key
        # -- unconfigured tiles render an "API KEY REQUIRED" watermark -- so Esri is used
        # instead.) Esri's Canvas/Imagery basemaps ship terrain shading and place-name labels as
        # two separate tile layers; the label layer for each style is added below as a
        # same-named "... Labels" overlay checkbox (folium always renders FeatureGroups/overlay
        # TileLayers as checkboxes, not radio buttons, so a true single-click "switch both at
        # once" control isn't available without custom JS) -- only the Dark Mode Labels overlay
        # is checked by default, matching the default Dark Mode base; switching base layers
        # requires also ticking the matching "... Labels" checkbox.
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            attr="Esri Dark Gray Canvas", name="Dark Mode", control=True, show=True,
        ).add_to(m)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery", name="Satellite", control=True, show=False,
        ).add_to(m)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}",
            attr="Esri Light Gray Canvas", name="Light Mode", control=True, show=False,
        ).add_to(m)

        # Label overlays (place names, boundaries) -- checkboxes, independent of base switching.
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
            attr="Esri Dark Gray Canvas", name="Dark Mode Labels", overlay=True, control=True, show=True,
        ).add_to(m)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
            attr="Esri World Imagery", name="Satellite Labels", overlay=True, control=True, show=False,
        ).add_to(m)
        folium.TileLayer(
            tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Reference/MapServer/tile/{z}/{y}/{x}",
            attr="Esri Light Gray Canvas", name="Light Mode Labels", overlay=True, control=True, show=False,
        ).add_to(m)

        # Add Layer Control to switch maps
        folium.LayerControl(position="topright").add_to(m)

        for row in df.itertuples(index=False):
            radius = 12 + row.pm25_current * 0.5
            folium.CircleMarker(
                location=[row.lat, row.lon],
                radius=radius,
                color=row.daqi_current_colour,
                fill=True,
                fill_color=row.daqi_current_colour,
                fill_opacity=0.8,
                popup=folium.Popup(
                    f"<b>{row.city_short}</b><br>"
                    f"PM2.5 now: {row.pm25_current} µg/m³<br>"
                    f"DAQI now: {row.daqi_current}<br>"
                    f"+24h forecast: {row.pm25_forecast_24h} µg/m³<br>"
                    f"+48h forecast: {row.pm25_forecast_48h} µg/m³",
                    max_width=250,
                ),
                tooltip=f"{row.city_short}: {row.pm25_current} µg/m³ ({row.daqi_current})",
            ).add_to(m)

        st_folium(m, height=450, use_container_width=True, returned_objects=[])

    with col_right:
        # Advice Card selector
        st.markdown("<h3 style='margin-bottom:5px;'>🩺 City Health Advisor</h3>", unsafe_allow_html=True)
        selected_city = st.selectbox("Select UK Study City:", df['city_short'].tolist())
        
        city_data = df[df['city_short'] == selected_city].iloc[0]
        advice = DAQI_ADVICE[city_data['daqi_current']]
        
        st.markdown(f"""
        <div style="background-color:#161b22; padding:25px; border-radius:12px; border:1px solid rgba(255,255,255,0.05); border-left:6px solid {advice['colour']}; box-shadow:0 4px 20px rgba(0,0,0,0.25);">
            <h4 style="margin:0 0 10px 0; color:#8892b0; font-size:12px; text-transform:uppercase; letter-spacing:0.5px;">Current Advisory</h4>
            <h2 style="margin:0 0 15px 0; color:#fafafa; font-weight:800; font-size:24px;">{advice['emoji']} {selected_city} — {city_data['daqi_current']}</h2>
            <p style="color:#fafafa; font-size:14px; line-height:1.6; margin-bottom:15px;"><b>Health Guidance:</b> {advice['advice']}</p>
            <hr style="border-color:rgba(255,255,255,0.05); margin:15px 0;">
            <p style="color:#8892b0; font-size:13px; margin:0;">
                Predicted band tomorrow (+24h): <b style="color:#fafafa;">{city_data['daqi_forecast']}</b><br>
                Predicted band day after (+48h): <b style="color:#fafafa;">{city_data['daqi_forecast_48h']}</b>
            </p>
        </div>
        """, unsafe_allow_html=True)

    # ---------------------------------------------------------------------------
    # Full Width 48-Hour Forecast Comparison Section
    # ---------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("## 📈 48-Hour Forecast Comparison")
    st.markdown("""
    XGBoost model output showing predicted PM2.5 at +24h and +48h from now.  
    The **Current (Live)** bar is the raw sensor reading — all other bars are **model predictions**.
    """)
    
    chart_df = pd.melt(
        df[["city_short", "pm25_current", "pm25_forecast_24h", "pm25_forecast_48h"]],
        id_vars="city_short",
        value_vars=["pm25_current", "pm25_forecast_24h", "pm25_forecast_48h"],
        var_name="Measurement",
        value_name="PM2.5 (µg/m³)",
    )
    chart_df["Measurement"] = chart_df["Measurement"].map({
        "pm25_current":      "Current",
        "pm25_forecast_24h": "+24h Forecast",
        "pm25_forecast_48h": "+48h Forecast",
    })

    fig = px.bar(
        chart_df,
        x="city_short",
        y="PM2.5 (µg/m³)",
        color="Measurement",
        barmode="group",
        labels={"city_short": "City"},
        color_discrete_map={"Current": "#58a6ff", "+24h Forecast": "#ED7D31", "+48h Forecast": "#8892b0"},
    )
    fig.add_hline(y=12, line_dash="dot", line_color="#F1C40F",
                  annotation_text="Moderate (12)", annotation_position="top left")
    fig.add_hline(y=24, line_dash="dot", line_color="#E67E22",
                  annotation_text="High (24)", annotation_position="top left")
    
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit", size=12, color="#FAFAFA"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0),
        height=320,
    )
    fig.update_xaxes(showgrid=False, color="#8892b0", title="")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#8892b0", title="PM2.5 (µg/m³)")
    st.plotly_chart(fig, use_container_width=True)

    # ---------------------------------------------------------------------------
    # Full Width Historical Trend Analysis Section
    # ---------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("## 📅 Historical Same-Day Trend Analysis")
    uk_tz = pytz.timezone("Europe/London")
    now_dt = datetime.datetime.now(uk_tz)
    date_str = now_dt.strftime("%d %B")
    st.markdown(f"Comparing current air quality levels against historical benchmarks for today's date ({date_str}).")
    
    # Chart 1: All Cities Grouped Bar
    st.markdown("<br><h3 style='margin-bottom:5px;'>1. Same-Day Multi-City Historical Baseline (2023 vs 2024 vs Today)</h3>", unsafe_allow_html=True)
    all_hist = get_all_cities_history()
    live_rows = []
    for city in CITIES:
        city_data_row = df[df['city_short'] == city["short"]].iloc[0]
        live_rows.append({
            "City": city["short"],
            "Year": "Today (Live)",
            "PM2.5 (µg/m³)": city_data_row["pm25_current"]
        })
    live_df = pd.DataFrame(live_rows)
    combined_all = pd.concat([all_hist, live_df], ignore_index=True)
    
    fig_all = px.bar(
        combined_all,
        x="City",
        y="PM2.5 (µg/m³)",
        color="Year",
        barmode="group",
        color_discrete_map={
            "2023": "#58a6ff", 
            "2024": "#ED7D31", 
            "Today (Live)": "#70AD47"
        }
    )
    fig_all.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Outfit", size=12, color="#FAFAFA"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=0, r=0, t=30, b=0),
        height=320,
    )
    fig_all.update_xaxes(showgrid=False, color="#8892b0", title="")
    fig_all.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#8892b0", title="PM2.5 (µg/m³)")
    st.plotly_chart(fig_all, use_container_width=True)

    # Chart 2: Hourly Line Comparison for Selected City
    st.markdown(f"<br><h3 style='margin-bottom:5px;'>2. Hourly Same-Day Trend Pattern for {selected_city} (2023 vs 2024 vs Today)</h3>", unsafe_allow_html=True)
    selected_city_data = df[df['city_short'] == selected_city].iloc[0]
    hist_df = get_city_history(
        selected_city, 
        pm25_current=selected_city_data['pm25_current'], 
        pm25_forecast_24h=selected_city_data['pm25_forecast_24h']
    )
    if not hist_df.empty:
        fig_hist = px.line(
            hist_df,
            x="Hour",
            y="PM2.5 (µg/m³)",
            color="Year",
            markers=True,
            height=280,
            color_discrete_map={
                "2023": "#58a6ff", 
                "2024": "#ED7D31", 
                "Current / Forecast": "#70AD47"
            }
        )
        fig_hist.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Outfit", size=12, color="#FAFAFA"),
            margin=dict(l=0, r=0, t=10, b=0),
            xaxis_title="Hour of Day",
            yaxis_title="PM2.5 (µg/m³)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_hist.update_xaxes(showgrid=False, color="#8892b0")
        fig_hist.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.05)", color="#8892b0")
        st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("---")
    st.markdown(
        """
        <div style="text-align:center; font-size:12px; color:#8892b0; padding:15px 0;">
            Data sources: DEFRA AURN (historical), OpenAQ v3 (live PM2.5), Open-Meteo (meteorological forecasts). 
            Model Pipeline: XGBoost Regressor trained on 2023-2024 study dataset.
        </div>
        """,
        unsafe_allow_html=True
    )

if False:  # with tab_insights (hidden):
    # Header Banner
    st.markdown("""
    <div style="background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); padding: 30px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.05); margin-bottom: 25px;">
        <h1 style="margin: 0; color: #fafafa; font-size: 32px; font-weight: 800;">📊 Model Evaluation & SHAP Explanations</h1>
        <p style="margin: 10px 0 0 0; color: #8892b0; font-size: 16px; font-weight: 400;">
            Performance metrics, model comparisons, and global/local SHAP transparency charts that support project validity.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col_eval_left, col_eval_right = st.columns(2)
    
    with col_eval_left:
        st.markdown("<h3 style='margin-bottom:10px;'>1. Model Performance Comparison</h3>", unsafe_allow_html=True)
        st.image(str(ROOT / "models" / "model_comparison_chart.png"), caption="RMSE and MAE evaluation metrics across Random Forest, XGBoost, and LSTM.", use_container_width=True)
        st.markdown("""
        <div style="font-size:14px; color:#8892b0; line-height:1.6; margin-top:10px;">
            We evaluated three primary algorithms. <b>XGBoost</b> was selected as the final production model due to achieving the lowest 
            RMSE (<b>5.14 µg/m³</b>) and superior classification mapping on the hold-out test set, followed closely by Random Forest 
            and Keras LSTM.
        </div>
        """, unsafe_allow_html=True)
        
    with col_eval_right:
        st.markdown("<h3 style='margin-bottom:10px;'>2. Predicted vs Actual Residual Analysis</h3>", unsafe_allow_html=True)
        st.image(str(ROOT / "models" / "forecast_vs_actual.png"), caption="Scatter plot showing regression fit accuracy on holdout test set.", use_container_width=True)
        st.markdown("""
        <div style="font-size:14px; color:#8892b0; line-height:1.6; margin-top:10px;">
            This residual chart demonstrates the model's high alignment. The proximity of predicted values to the ideal diagonal line 
            proves the model's reliability in identifying true peaks and low-risk baseline days.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin:30px 0;'>", unsafe_allow_html=True)
    
    col_shap_left, col_shap_right = st.columns(2)
    
    with col_shap_left:
        st.markdown("<h3 style='margin-bottom:10px;'>3. Global Feature Impact (SHAP Bar Chart)</h3>", unsafe_allow_html=True)
        st.image(str(ROOT / "models" / "shap_global_bar.png"), caption="Feature impact hierarchy sorted by mean absolute SHAP value.", use_container_width=True)
        st.markdown("""
        <div style="font-size:14px; color:#8892b0; line-height:1.6; margin-top:10px;">
            The SHAP summary bar chart highlights that <b>Yesterday's PM2.5 levels (pm25_lag_24)</b> and <b>Recent 24h Average PM2.5 (pm25_roll_24h)</b> 
            exert the strongest mathematical weight on predictions, verifying time-series persistence.
        </div>
        """, unsafe_allow_html=True)

    with col_shap_right:
        st.markdown("<h3 style='margin-bottom:10px;'>4. Directional Impact (SHAP Beeswarm Plot)</h3>", unsafe_allow_html=True)
        st.image(str(ROOT / "models" / "shap_beeswarm.png"), caption="Beeswarm plot showing directional influence of features.", use_container_width=True)
        st.markdown("""
        <div style="font-size:14px; color:#8892b0; line-height:1.6; margin-top:10px;">
            The beeswarm plot demonstrates directional physical associations. For instance, high <b>wind speed (red dots)</b> is shown 
            shifting prediction impacts to the left (negative SHAP impact), matching meteorological theory that high wind disperses pollutants.
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(255,255,255,0.05); margin:30px 0;'>", unsafe_allow_html=True)
    
    col_water_left, col_water_right = st.columns(2)
    
    with col_water_left:
        st.markdown("<h3 style='margin-bottom:10px;'>5. Local Decision Explanation (Waterfall Plot 1)</h3>", unsafe_allow_html=True)
        st.image(str(ROOT / "models" / "shap_waterfall_1.png"), caption="Waterfall explanation for a high-risk pollution day.", use_container_width=True)
        st.markdown("""
        <div style="font-size:14px; color:#8892b0; line-height:1.6; margin-top:10px;">
            Waterfall plots explain decisions for specific daily predictions. In this high-risk scenario, the model output is pushed 
            significantly above the base average primarily due to elevated lag PM2.5 values.
        </div>
        """, unsafe_allow_html=True)

    with col_water_right:
        st.markdown("<h3 style='margin-bottom:10px;'>6. Local Decision Explanation (Waterfall Plot 2)</h3>", unsafe_allow_html=True)
        st.image(str(ROOT / "models" / "shap_waterfall_2.png"), caption="Waterfall explanation for a moderate-risk baseline day.", use_container_width=True)
        st.markdown("""
        <div style="font-size:14px; color:#8892b0; line-height:1.6; margin-top:10px;">
            For this moderate-risk prediction, the model output stays close to the baseline average due to stable meteorological features
            and moderate yesterday-lags.
        </div>
        """, unsafe_allow_html=True)


# ===========================================================================
# TAB 2 — Custom Air Quality Predictor
# ===========================================================================

with tab_predictor:
    import datetime as _dt

    # ── Hero Banner ─────────────────────────────────────────────────────────────
    st.markdown("""
<div style="background:linear-gradient(135deg,#1a1f2e 0%,#0d1117 100%);
            padding:30px; border-radius:14px;
            border:1px solid rgba(255,255,255,0.06); margin-bottom:24px;">
  <h1 style="margin:0;color:#fafafa;font-size:30px;font-weight:800;">
    🔮 Custom Air Quality Predictor
  </h1>
  <p style="margin:10px 0 0;color:#8892b0;font-size:15px;">
    Choose any UK city, date and hour — our <b style="color:#58a6ff;">XGBoost model</b>
    will predict the expected PM2.5 concentration and DAQI risk level using
    real weather data from Open-Meteo.
  </p>
</div>
""", unsafe_allow_html=True)

    # ── How it works (expander) ─────────────────────────────────────────────────
    with st.expander("ℹ️  How does this work?", expanded=False):
        st.markdown("""
**What is PM2.5?**
PM2.5 refers to fine particulate matter smaller than 2.5 micrometres — invisible to the naked eye but able
to penetrate deep into the lungs and enter the bloodstream. It is the primary air-quality metric tracked
by UK, WHO and EU health guidelines.

**What is DAQI?**
The **Daily Air Quality Index (DAQI)** is the UK government's 10-point scale, grouped into four risk bands:
- 🟢 **Low (1–3)** — PM2.5 < 12 µg/m³: safe for everyone
- 🟡 **Moderate (4–6)** — PM2.5 12–24 µg/m³: sensitive groups should take care
- 🟠 **High (7–9)** — PM2.5 24–48 µg/m³: everyone may feel effects
- 🔴 **Very High (10)** — PM2.5 ≥ 48 µg/m³: serious health risk

**How does the prediction work?**
The model uses **19 input features** across three groups:
1. 🌦️ **Weather** — temperature, humidity, wind speed/direction, rain, pressure (fetched live from Open-Meteo)
2. 🕐 **Time context** — hour of day, weekday, month, weekend flag
3. 📊 **Recent air quality** — 1h / 2h / 3h / 24h PM2.5 lags + 24h/72h rolling averages (from DEFRA AURN records)

For **past dates**, real archived weather is fetched. For **future dates**, the forecast API is used.
PM2.5 lag features are derived from the closest available AURN historical data.

> ⚠️ **Note**: Predictions are most accurate within the model's training window (2023–2024). Future dates
> and dates far outside that window use seasonal proxies for lag features and carry higher uncertainty.
        """)

    st.markdown("---")

    # ── Input Form ──────────────────────────────────────────────────────────────
    st.markdown("### 🎛️ Configure Your Prediction")

    with st.form("predictor_form"):
        fc1, fc2, fc3 = st.columns([1.5, 1.5, 1])

        with fc1:
            pred_city = st.selectbox(
                "🏙️ Select City",
                [c["short"] for c in CITIES],
                help="One of the 5 UK cities monitored in this study."
            )
        with fc2:
            pred_date = st.date_input(
                "📅 Select Date",
                value=_dt.date.today(),
                min_value=_dt.date(2023, 1, 1),
                max_value=_dt.date.today() + _dt.timedelta(days=14),
                help="Historical dates use real archived weather; future dates use the forecast API."
            )
        with fc3:
            pred_hour = st.slider(
                "🕐 Hour of Day",
                min_value=0, max_value=23,
                value=_dt.datetime.now().hour,
                format="%d:00",
                help="0 = midnight, 12 = noon, 23 = 11 PM"
            )

        submitted = st.form_submit_button(
            "▶  Run Prediction",
            use_container_width=True,
            type="primary",
        )

    # ── Results ─────────────────────────────────────────────────────────────────
    if submitted:
        target_dt = _dt.datetime.combine(pred_date, _dt.time(pred_hour, 0))
        dt_label  = target_dt.strftime("%A %d %B %Y at %H:00")

        with st.spinner(f"Fetching weather & running XGBoost for {pred_city} on {dt_label}..."):
            result = predict_custom(pred_city, target_dt)

        pm25_val  = result["pm25_predicted"]
        band      = result["daqi_band"]
        colour    = result["daqi_colour"]
        wx        = result["weather"]
        feats     = result["features"]
        data_note = result["data_note"]
        advice    = DAQI_ADVICE[band]

        # ── Top result card ──────────────────────────────────────────────────────
        WHO_LIMIT = 15   # WHO annual mean guideline µg/m³
        UK_LIMIT  = 20   # UK national objective µg/m³
        pct_who   = min(100, round(pm25_val / WHO_LIMIT * 100))
        pct_uk    = min(100, round(pm25_val / UK_LIMIT  * 100))

        compass_dirs = ["N","NE","E","SE","S","SW","W","NW"]
        wdir_label   = compass_dirs[round(float(wx.get("wind_direction_10m", 0)) / 45) % 8]

        st.markdown(f"""
<div style="background:linear-gradient(135deg,{advice['bg_alpha']},{advice['bg_alpha']}),
            linear-gradient(135deg,#161b22,#0d1117);
            border:1px solid {colour}33; border-left:5px solid {colour};
            border-radius:14px; padding:24px 28px; margin:16px 0;">
  <div style="font-size:13px;color:#8892b0;margin-bottom:6px;">📍 {pred_city} &nbsp;·&nbsp; {dt_label}</div>
  <div style="display:flex;align-items:center;gap:24px;flex-wrap:wrap;">
    <div>
      <div style="font-size:11px;color:#8892b0;text-transform:uppercase;letter-spacing:1px;">Predicted PM2.5</div>
      <div style="font-size:64px;font-weight:800;color:{colour};line-height:1.05;">{pm25_val}</div>
      <div style="font-size:14px;color:#8892b0;">µg/m³</div>
    </div>
    <div style="flex:1;min-width:200px;">
      <div style="font-size:22px;font-weight:700;color:#fafafa;margin-bottom:6px;">
        {advice['emoji']} DAQI &nbsp;—&nbsp; {band}
      </div>
      <div style="font-size:14px;color:#a3acb9;line-height:1.6;">{advice['advice']}</div>
    </div>
  </div>
  <div style="margin-top:16px;">
    <div style="font-size:11px;color:#8892b0;margin-bottom:4px;">vs WHO Annual Mean Guideline (15 µg/m³)</div>
    <div style="background:rgba(255,255,255,0.06);border-radius:6px;height:10px;overflow:hidden;">
      <div style="background:{colour};width:{pct_who}%;height:100%;border-radius:6px;transition:width 0.5s ease;"></div>
    </div>
    <div style="font-size:11px;color:#636d7e;margin-top:3px;">{pm25_val} µg/m³ = {pct_who}% of WHO limit</div>
  </div>
  <div style="margin-top:10px;">
    <div style="font-size:11px;color:#8892b0;margin-bottom:4px;">vs UK National Objective (20 µg/m³)</div>
    <div style="background:rgba(255,255,255,0.06);border-radius:6px;height:10px;overflow:hidden;">
      <div style="background:{colour};width:{pct_uk}%;height:100%;border-radius:6px;"></div>
    </div>
    <div style="font-size:11px;color:#636d7e;margin-top:3px;">{pm25_val} µg/m³ = {pct_uk}% of UK limit</div>
  </div>
</div>
""", unsafe_allow_html=True)

        # ── Gauge + Weather conditions ─────────────────────────────────────────
        col_gauge, col_wx = st.columns([1, 1.8])

        with col_gauge:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pm25_val,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "PM2.5 µg/m³", "font": {"size": 14, "color": "#a3acb9", "family": "Outfit"}},
                number={"suffix": "", "font": {"size": 40, "color": colour, "family": "Outfit"}},
                gauge={
                    "axis": {"range": [0, 60], "tickcolor": "#636d7e",
                             "tickfont": {"color": "#636d7e", "size": 10}},
                    "bar": {"color": colour, "thickness": 0.25},
                    "bgcolor": "rgba(0,0,0,0)",
                    "borderwidth": 0,
                    "threshold": {
                        "line": {"color": "#F1C40F", "width": 3},
                        "thickness": 0.8, "value": 15,
                    },
                    "steps": [
                        {"range": [0, 12],  "color": "rgba(46,204,113,0.12)"},
                        {"range": [12, 24], "color": "rgba(241,196,15,0.12)"},
                        {"range": [24, 48], "color": "rgba(230,126,34,0.12)"},
                        {"range": [48, 60], "color": "rgba(231,76,60,0.12)"},
                    ],
                },
            ))
            fig_gauge.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=240, margin=dict(l=10, r=10, t=30, b=10),
                font=dict(family="Outfit", color="#fafafa"),
            )
            st.plotly_chart(fig_gauge, use_container_width=True, key="pred_gauge")
            st.caption("🟡 Yellow line = WHO guideline (15 µg/m³)")

        with col_wx:
            st.markdown("**🌦️ Weather conditions used for this prediction**")
            wx_items = [
                ("🌡️", "Temperature",   f"{wx.get('temperature_2m',0)}°C"),
                ("💧", "Humidity",       f"{wx.get('relative_humidity_2m',0)}%"),
                ("🌬️", "Wind Speed",    f"{wx.get('wind_speed_10m',0)} km/h"),
                ("🧭", "Wind Direction", f"{wdir_label} ({int(wx.get('wind_direction_10m',0))}°)"),
                ("🌧️", "Precipitation", f"{wx.get('precipitation',0)} mm"),
                ("⏱️", "Pressure",      f"{wx.get('surface_pressure',0)} hPa"),
            ]
            wx_r1, wx_r2 = st.columns(2)
            for idx_wx, (icon, label, val) in enumerate(wx_items):
                with (wx_r1 if idx_wx % 2 == 0 else wx_r2):
                    st.markdown(f"""
<div style="background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.06);
            border-radius:10px;padding:12px 14px;margin-bottom:8px;display:flex;
            align-items:center;gap:10px;">
  <span style="font-size:22px;">{icon}</span>
  <div>
    <div style="font-size:10px;color:#636d7e;text-transform:uppercase;letter-spacing:0.5px;">{label}</div>
    <div style="font-size:16px;font-weight:700;color:#fafafa;">{val}</div>
  </div>
</div>""", unsafe_allow_html=True)

        # ── Why this prediction? (live SHAP explanation) ─────────────────────
        st.markdown("---")
        st.markdown("**🔍 Why this prediction?**")

        shap_feats = result.get("shap_top_features", [])
        if shap_feats:
            FEATURE_LABELS = {
                "pm25": "Recent PM2.5 reading",
                "pm25_lag_1": "PM2.5, 1 hour before",
                "pm25_lag_2": "PM2.5, 2 hours before",
                "pm25_lag_3": "PM2.5, 3 hours before",
                "pm25_lag_24": "PM2.5, 24 hours before",
                "pm25_roll_24h": "24h average PM2.5",
                "pm25_roll_72h": "72h average PM2.5",
                "o3": "Ozone level",
                "no2": "Nitrogen dioxide level",
                "temperature_2m": "Temperature",
                "relative_humidity_2m": "Humidity",
                "wind_speed_10m": "Wind speed",
                "wind_direction_10m": "Wind direction",
                "precipitation": "Precipitation",
                "surface_pressure": "Surface pressure",
                "hour": "Time of day",
                "day_of_week": "Day of week",
                "month": "Month of year",
                "is_weekend": "Weekend/weekday",
            }
            ordered = sorted(shap_feats, key=lambda d: abs(d["shap_value"]))
            labels  = [FEATURE_LABELS.get(d["feature"], d["feature"]) for d in ordered]
            values  = [d["shap_value"] for d in ordered]
            colours = ["#E74C3C" if v > 0 else "#3498DB" for v in values]

            fig_shap = go.Figure(go.Bar(
                x=values, y=labels, orientation="h",
                marker_color=colours,
                text=[f"{v:+.2f}" for v in values],
                textposition="outside",
            ))
            fig_shap.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=260, margin=dict(l=10, r=30, t=10, b=10),
                font=dict(family="Outfit", color="#fafafa", size=12),
                xaxis=dict(title="Impact on predicted PM2.5 (µg/m³)", gridcolor="rgba(255,255,255,0.06)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
            )
            st.plotly_chart(fig_shap, use_container_width=True, key="pred_shap")
            st.caption("🔴 Red = pushes PM2.5 higher &nbsp;·&nbsp; 🔵 Blue = pushes PM2.5 lower")

            top = ordered[-1]
            top_label = FEATURE_LABELS.get(top["feature"], top["feature"])
            direction = "the biggest upward influence on" if top["shap_value"] > 0 else "the biggest downward influence on"
            st.markdown(
                f"<div style='font-size:14px;color:#a3acb9;margin-top:6px;'>"
                f"<b style='color:#fafafa;'>{top_label}</b> (value: {top['feature_value']}) had "
                f"{direction} this prediction.</div>",
                unsafe_allow_html=True,
            )

        # ── DAQI Reference Guide ─────────────────────────────────────────────
        st.markdown("---")
        st.markdown("**📋 DAQI Reference Guide — what each band means for you**")
        ref_cols = st.columns(4)
        daqi_ref = [
            ("🟢","Low",      "< 12 µg/m³",  "#2ECC71","rgba(46,204,113,0.1)",
             "Air quality is good. All outdoor activities are fine, including for sensitive groups."),
            ("🟡","Moderate", "12–24 µg/m³","#F1C40F","rgba(241,196,15,0.1)",
             "Sensitive groups (asthma, heart conditions, elderly, children) should reduce prolonged strenuous outdoor exertion."),
            ("🟠","High",     "24–48 µg/m³","#E67E22","rgba(230,126,34,0.1)",
             "Everyone may experience health effects. Reduce prolonged or heavy outdoor activity — especially near busy roads."),
            ("🔴","Very High","≥ 48 µg/m³", "#E74C3C","rgba(231,76,60,0.1)",
             "Serious health alert for all. Avoid outdoor exertion. At-risk individuals should stay indoors with windows closed."),
        ]
        for (emoji, label, range_txt, col, bg, tip), ref_col in zip(daqi_ref, ref_cols):
            is_current = (label == band)
            border = f"2px solid {col}" if is_current else "1px solid rgba(255,255,255,0.06)"
            active_badge = (
                f'<div style="margin-top:10px;font-size:10px;color:{col};font-weight:700;'
                f'text-transform:uppercase;letter-spacing:1px;">◄ Your Result</div>'
            ) if is_current else ""
            with ref_col:
                st.markdown(f"""
<div style="background:{bg};border:{border};border-radius:12px;padding:16px 14px;">
  <div style="font-size:28px;margin-bottom:6px;">{emoji}</div>
  <div style="font-size:14px;font-weight:700;color:{col};margin-bottom:2px;">{label}</div>
  <div style="font-size:11px;color:#a3acb9;margin-bottom:8px;font-weight:600;">{range_txt}</div>
  <div style="font-size:12px;color:#8892b0;line-height:1.5;">{tip}</div>
  {active_badge}
</div>""", unsafe_allow_html=True)

    else:
        # ── Placeholder shown before first submission ─────────────────────────
        st.markdown("""
<div style="background:rgba(255,255,255,0.02);border:1px dashed rgba(88,166,255,0.3);
            border-radius:14px;padding:60px 40px;text-align:center;margin:20px 0;">
  <div style="font-size:56px;margin-bottom:16px;">🔮</div>
  <div style="font-size:20px;font-weight:700;color:#fafafa;margin-bottom:8px;">
    Configure your prediction above
  </div>
  <div style="font-size:14px;color:#636d7e;max-width:420px;margin:0 auto;line-height:1.6;">
    Select a city, pick any date from 2023 onwards, choose the hour, then click
    <b style="color:#58a6ff;">▶ Run Prediction</b> to see the XGBoost model's PM2.5 estimate
    and full health advisory.
  </div>
</div>
""", unsafe_allow_html=True)

        # Always-visible DAQI quick reference
        st.markdown("#### Quick DAQI Reference")
        for emoji, label, range_txt, col, bg, tip in [
            ("🟢","Low",      "< 12 µg/m³",  "#2ECC71","rgba(46,204,113,0.08)","Safe for everyone."),
            ("🟡","Moderate", "12–24 µg/m³","#F1C40F","rgba(241,196,15,0.08)","Sensitive groups should take care."),
            ("🟠","High",     "24–48 µg/m³","#E67E22","rgba(230,126,34,0.08)","Everyone may feel health effects."),
            ("🔴","Very High","≥ 48 µg/m³", "#E74C3C","rgba(231,76,60,0.08)","Serious health risk for all."),
        ]:
            st.markdown(f"""
<div style="background:{bg};border:1px solid rgba(255,255,255,0.05);border-left:4px solid {col};
            border-radius:8px;padding:12px 16px;margin-bottom:6px;
            display:flex;align-items:center;gap:12px;">
  <span style="font-size:20px;">{emoji}</span>
  <div>
    <b style="color:{col};">{label}</b>
    <span style="color:#8892b0;font-size:12px;"> &nbsp;{range_txt}&nbsp; — &nbsp;{tip}</span>
  </div>
</div>""", unsafe_allow_html=True)
