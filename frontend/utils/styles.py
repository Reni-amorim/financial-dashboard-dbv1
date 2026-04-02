import streamlit as st

def aplicar_estilos():
    st.markdown("""
    <style>
        /* Cards / Metrics */
        div[data-testid="stMetric"] {
            background-color: #d3d3d3 !important;
            border-radius: 8px;
            padding: 12px;
        }

        /* Texto dos cards */
        div[data-testid="stMetric"] label,
        div[data-testid="stMetricValue"] > div,
        div[data-testid="stMetricDelta"] > div,
        div[data-testid="stMetricLabel"] > div {
            color: #262730 !important;
        }
    </style>
    """, unsafe_allow_html=True)