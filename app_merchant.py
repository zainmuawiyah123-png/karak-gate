import os
import re
import sqlite3
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Halago", page_icon="🔔", layout="wide"
)

st.markdown(
    """
    <style>
    /* إخفاء شريط القائمة العلوي وترويسة Streamlit بالكامل وأزرار النشر و GitHub Fork */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display: none;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    .stApp {
        background-color: #FF5722 !important;
        color: #000000 !important;
    }
    h1, h2, h3, h4, h5, h6, p, label, span {
        color: #000000 !important;
    }
    .stButton>button {
        border-radius: 8px;
        font-weight: bold;
        border: none;
        background-color: #FFFFFF !important;
        color: #FF5722 !important;
    }
    .stButton>button:hover {
        background-color: #FFF3E0 !important;
        color: #E64A19 !important;
    }
    .merchant-card {
        background-color: #FFFFFF;
        padding: 20px;
        border-radius: 12px;
        margin-bottom: 15px;
        border: 2px solid #E0E0E0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .merchant-card h4, .merchant-card p, .merchant-card span {
        color: #000000 !important;
    }
    .item-card {
        background-color: #FFF3E0;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        border: 1px solid #FFCC80;
    }
    .item-card p {
        color: #000000 !important;
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.05); }
        100% { transform: scale(1); }
    }
    .bell-alert {
        background-color: #B71C1C;
        color: white !important;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        font-weight: bold;
        font-size: 20px;
        animation:
