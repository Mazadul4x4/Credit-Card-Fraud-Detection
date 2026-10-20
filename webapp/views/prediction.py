import pandas as pd
import streamlit as st

import api_client

NUMERIC = ["Time"] + [f"V{i}" for i in range(1, 29)] + ["Amount"]
TIME_PERIODS = ["night", "morning", "afternoon", "evening"]
FEATURES = NUMERIC + ["time_period"]

st.title("💳 Fraud prediction")

try:
    info = api_client.health()
    if info["model_loaded"]:
        st.caption(f"API connected | model `{info['model_version']}`")
    else:
        st.warning("API is running but no model is loaded.")
except Exception as exc:  # noqa: BLE001
    st.error(f"Cannot reach the API: {exc}")
    st.stop()


def show_results(features: pd.DataFrame, response: dict) -> None:
    results = pd.DataFrame(response["predictions"])[["label", "fraud_probability"]]
    table = pd.concat([results, features.reset_index(drop=True)], axis=1)
    frauds = int((results["label"] == "fraud").sum())
    st.success(
        f"{response['count']} prediction(s) | {frauds} flagged as fraud | model {response['model_version']}"
    )
    st.dataframe(table, use_container_width=True, hide_index=True)


single, batch = st.tabs(["Single transaction", "Multiple transactions (CSV)"])

with single:
    with st.form("single_prediction"):
        c1, c2, c3 = st.columns(3)
        time_value = c1.number_input("Time (seconds)", min_value=0.0, value=40000.0, step=1.0)
        amount = c2.number_input("Amount", min_value=0.0, value=100.0, step=1.0)
        period = c3.selectbox("Time period", TIME_PERIODS, index=1)
        st.markdown("**PCA features V1 to V28**")
        v_values = {}
        cols = st.columns(7)
        for i in range(1, 29):
            v_values[f"V{i}"] = cols[(i - 1) % 7].number_input(f"V{i}", value=0.0, format="%.4f")
        submitted = st.form_submit_button("Predict", type="primary")

    if submitted:
        transaction = {"Time": time_value, "Amount": amount, "time_period": period, **v_values}
        try:
            response = api_client.predict([transaction])
            show_results(pd.DataFrame([transaction])[FEATURES], response)
        except api_client.ApiError as exc:
            st.error(str(exc))

with batch:
    uploaded = st.file_uploader("CSV file with the feature columns", type="csv")
    if uploaded is not None:
        df = pd.read_csv(uploaded)
        missing = [c for c in FEATURES if c not in df.columns]
        if missing:
            st.error(f"Missing columns: {', '.join(missing)}")
        else:
            st.write(f"{len(df)} rows loaded")
            st.dataframe(df.head(), use_container_width=True, hide_index=True)
            if st.button("Predict all", type="primary"):
                keep = (["transaction_id"] if "transaction_id" in df.columns else []) + FEATURES
                records = df[keep].to_dict(orient="records")
                try:
                    response = api_client.predict(records)  # ONE call for the whole file
                    show_results(df[FEATURES], response)
                except api_client.ApiError as exc:
                    st.error(str(exc))
