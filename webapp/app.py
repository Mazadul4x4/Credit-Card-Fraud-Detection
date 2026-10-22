import streamlit as st

st.set_page_config(page_title="Credit Card Fraud Detection", page_icon="💳", layout="wide")

pages = st.navigation(
    [
        st.Page("views/prediction.py", title="Prediction", icon="🔍"),
        st.Page("views/past_predictions.py", title="Past predictions", icon="📜"),
    ]
)
pages.run()
