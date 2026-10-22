import os
import socket
from datetime import datetime, time, timedelta, timezone

import pandas as pd
import requests
import streamlit as st

# Determine API URL based on environment
default_api = "http://api:8000"
if "@api:" in default_api or default_api == "http://api:8000":
    try:
        socket.gethostbyname("api")
        resolved_api = "http://api:8000"
    except Exception:
        resolved_api = "http://localhost:8000"
else:
    resolved_api = "http://localhost:8000"

API_URL = os.getenv("API_URL", resolved_api)

st.set_page_config(
    page_title="GuardianAI — Credit Card Fraud Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .metric-card {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.05) 0%, rgba(255, 255, 255, 0.02) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 18px 24px;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.2);
        margin-bottom: 12px;
    }

    .badge-fraud {
        background-color: #ff3366;
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.95rem;
        display: inline-block;
        box-shadow: 0 0 15px rgba(255, 51, 102, 0.4);
    }

    .badge-legit {
        background-color: #00d26a;
        color: white;
        padding: 6px 14px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 0.95rem;
        display: inline-block;
        box-shadow: 0 0 15px rgba(0, 210, 106, 0.4);
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Sidebar
st.sidebar.image("https://img.icons8.com/fluency/96/bank-card-back-side.png", width=64)
st.sidebar.title("GuardianAI")
st.sidebar.caption("Machine Learning Fraud Defense System")

# Health Check
try:
    health_resp = requests.get(f"{API_URL}/health", timeout=3)
    if health_resp.status_code == 200:
        h_data = health_resp.json()
        model_ver = h_data.get("model_version", "1.0.0")
        st.sidebar.success(f"● Connected to API (v{model_ver})")
    else:
        st.sidebar.warning("API responded with warning")
except Exception:
    st.sidebar.error("✖ API Service Disconnected")
    st.error(f"Cannot reach FastAPI backend at `{API_URL}`. Ensure the service is running.")

menu_selection = st.sidebar.radio(
    "Navigation",
    ["Fraud Prediction Engine", "Audit Trail & History"],
    index=0,
)

st.sidebar.divider()
st.sidebar.info(
    "**End-to-End MLOps Pipeline**\n"
    "- Great Expectations data quality checks\n"
    "- Automated Airflow ingestion & scoring\n"
    "- Single-transaction and batch API inference"
)

# ----------------------------------------------------
# PAGE 1: PREDICTION ENGINE (FORM + CSV)
# ----------------------------------------------------
if menu_selection == "Fraud Prediction Engine":
    st.title("🛡️ Fraud Prediction Engine")
    st.markdown("Real-time inference via trained Random Forest pipeline with feature persistence.")

    tab_form, tab_csv = st.tabs(["📝 Single Transaction Form", "📁 Batch CSV Scoring"])

    # TAB 1: FORM INPUT
    with tab_form:
        st.subheader("Manual Transaction Input")
        st.write("Enter transaction features or load realistic preset profiles.")

        col_sample1, col_sample2, col_sample3 = st.columns([1, 1, 2])
        if col_sample1.button("Preset: Normal Transaction"):
            st.session_state["f_time"] = 406.0
            st.session_state["f_amount"] = 29.99
            st.session_state["f_v1"] = -0.32
            st.session_state["f_v2"] = 0.54
            st.session_state["f_v3"] = 1.12
            st.session_state["f_v4"] = -0.45

        if col_sample2.button("Preset: High-Risk Profile"):
            st.session_state["f_time"] = 406.0
            st.session_state["f_amount"] = 899.50
            st.session_state["f_v1"] = -2.31
            st.session_state["f_v2"] = 1.95
            st.session_state["f_v3"] = -1.60
            st.session_state["f_v4"] = 3.99

        with st.form("single_prediction_form"):
            c1, c2 = st.columns(2)
            with c1:
                t_val = st.number_input("Time (seconds)", value=float(st.session_state.get("f_time", 100.0)), step=1.0)
            with c2:
                amt_val = st.number_input("Amount ($)", value=float(st.session_state.get("f_amount", 45.00)), step=1.0, min_value=0.0)

            st.write("Principal Component Features (V1 - V4 prominent, V5 - V28 defaults):")
            col_v1, col_v2, col_v3, col_v4 = st.columns(4)
            v1_val = col_v1.number_input("V1", value=float(st.session_state.get("f_v1", 0.0)), step=0.1)
            v2_val = col_v2.number_input("V2", value=float(st.session_state.get("f_v2", 0.0)), step=0.1)
            v3_val = col_v3.number_input("V3", value=float(st.session_state.get("f_v3", 0.0)), step=0.1)
            v4_val = col_v4.number_input("V4", value=float(st.session_state.get("f_v4", 0.0)), step=0.1)

            with st.expander("Show Additional Features (V5 to V28)"):
                v_others = {}
                cols_grid = st.columns(4)
                for i in range(5, 29):
                    col_target = cols_grid[(i - 5) % 4]
                    v_others[f"V{i}"] = col_target.number_input(f"V{i}", value=0.0, step=0.1)

            submit_btn = st.form_submit_button("🔍 Run Fraud Assessment", use_container_width=True)

        if submit_btn:
            tx_data = {
                "Time": t_val,
                "Amount": amt_val,
                "V1": v1_val,
                "V2": v2_val,
                "V3": v3_val,
                "V4": v4_val,
            }
            tx_data.update(v_others)

            payload = {
                "transaction": tx_data,
                "source": "streamlit_form",
            }

            try:
                with st.spinner("Analyzing transaction with fraud detection model..."):
                    res = requests.post(f"{API_URL}/predict/single", json=payload, timeout=10)

                if res.status_code == 200:
                    data = res.json()
                    is_fraud = data["predicted_class"] == 1
                    prob = data["probability"]

                    st.divider()
                    res_col1, res_col2 = st.columns([1, 2])
                    with res_col1:
                        if is_fraud:
                            st.markdown('<div class="badge-fraud">🚨 FRAUD DETECTED</div>', unsafe_allow_html=True)
                        else:
                            st.markdown('<div class="badge-legit">🛡️ LEGITIMATE TRANSACTION</div>', unsafe_allow_html=True)

                        st.metric("Fraud Probability", f"{prob * 100:.2f}%")
                        st.progress(float(prob))

                    with res_col2:
                        st.markdown(
                            f"""
                            **Audit Metadata:**
                            - **Prediction ID:** `{data['id']}`
                            - **Classification:** `{'Fraud' if is_fraud else 'Legitimate'}`
                            - **Confidence:** `{prob:.4f}`
                            - **Model Version:** `{data['model_version']}`
                            - **Trigger Source:** `{data['source']}`
                            - **Timestamp:** `{data['created_at']}`
                            """
                        )
                    st.success("Transaction prediction stored in database.")
                else:
                    st.error(f"Inference failed (HTTP {res.status_code}): {res.text}")
            except Exception as e:
                st.error(f"Prediction request error: {e}")

    # TAB 2: BATCH CSV
    with tab_csv:
        st.subheader("Batch File Processing")
        st.write("Upload a CSV file containing credit card transactions to perform high-throughput batch inference.")

        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

        if uploaded_file is not None:
            try:
                df_upload = pd.read_csv(uploaded_file)
                st.info(f"Loaded file `{uploaded_file.name}` containing **{len(df_upload)}** rows and **{len(df_upload.columns)}** columns.")
                st.dataframe(df_upload.head(5), use_container_width=True)

                if st.button("🚀 Score All Transactions", type="primary"):
                    records = df_upload.to_dict(orient="records")
                    batch_payload = {
                        "transactions": records,
                        "source": "streamlit_csv",
                    }

                    with st.spinner(f"Scoring {len(records)} transactions in one batch API call..."):
                        b_resp = requests.post(f"{API_URL}/predict", json=batch_payload, timeout=60)

                    if b_resp.status_code == 200:
                        b_data = b_resp.json()
                        pred_list = b_data["predictions"]
                        total_scored = len(pred_list)

                        fraud_count = sum(1 for p in pred_list if p["predicted_class"] == 1)
                        legit_count = total_scored - fraud_count
                        fraud_pct = (fraud_count / total_scored * 100) if total_scored > 0 else 0

                        st.divider()
                        m1, m2, m3, m4 = st.columns(4)
                        m1.metric("Total Scored", total_scored)
                        m2.metric("Legitimate", legit_count)
                        m3.metric("Fraudulent Flagged", fraud_count)
                        m4.metric("Fraud Rate", f"{fraud_pct:.2f}%")

                        res_df = pd.DataFrame([
                            {
                                "ID": p["id"],
                                "Class": "🚨 FRAUD" if p["predicted_class"] == 1 else "✅ Legit",
                                "Probability": round(p["probability"], 4),
                                "Source": p["source"],
                                "Timestamp": p["created_at"],
                            }
                            for p in pred_list
                        ])

                        st.dataframe(res_df, use_container_width=True)

                        csv_out = res_df.to_csv(index=False).encode("utf-8")
                        st.download_button(
                            label="📥 Download Scored Results (CSV)",
                            data=csv_out,
                            file_name=f"scored_{uploaded_file.name}",
                            mime="text/csv",
                        )
                        st.success(f"All {total_scored} predictions saved to Postgres database.")
                    else:
                        st.error(f"Batch prediction failed: {b_resp.text}")
            except Exception as e:
                st.error(f"Error parsing uploaded file: {e}")

# ----------------------------------------------------
# PAGE 2: PAST PREDICTIONS (DATES + SOURCE FILTER)
# ----------------------------------------------------
elif menu_selection == "Audit Trail & History":
    st.title("📊 Past Predictions & Audit Trail")
    st.markdown("Query and inspect historical predictions stored in PostgreSQL with filtering by date range and ingestion source.")

    # Filter Controls
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.5, 1.5, 1.5, 1])

    with filter_col1:
        default_start = (datetime.now(timezone.utc) - timedelta(days=7)).date()
        start_d = st.date_input("Start Date", value=default_start)

    with filter_col2:
        default_end = datetime.now(timezone.utc).date()
        end_d = st.date_input("End Date", value=default_end)

    with filter_col3:
        source_opts = ["All Sources", "Prediction DAG", "streamlit_form", "streamlit_csv", "pytest_test"]
        selected_source = st.selectbox("Source Filter", source_opts, index=0)

    with filter_col4:
        limit_val = st.number_input("Limit", value=100, min_value=10, max_value=1000, step=50)

    params = {"limit": limit_val}
    if start_d:
        dt_start = datetime.combine(start_d, time.min).replace(tzinfo=timezone.utc)
        params["start_date"] = dt_start.isoformat()
    if end_d:
        dt_end = datetime.combine(end_d, time.max).replace(tzinfo=timezone.utc)
        params["end_date"] = dt_end.isoformat()
    if selected_source != "All Sources":
        params["source"] = selected_source

    try:
        with st.spinner("Fetching predictions from database..."):
            hist_resp = requests.get(f"{API_URL}/predictions", params=params, timeout=10)

        if hist_resp.status_code == 200:
            hist_data = hist_resp.json()

            if not hist_data:
                st.info("No predictions found matching the selected filter criteria.")
            else:
                total_retrieved = len(hist_data)
                fraud_retrieved = sum(1 for h in hist_data if h["predicted_class"] == 1)
                fraud_rate = (fraud_retrieved / total_retrieved * 100) if total_retrieved > 0 else 0

                c_m1, c_m2, c_m3 = st.columns(3)
                c_m1.metric("Retrieved Records", total_retrieved)
                c_m2.metric("Fraud Records", fraud_retrieved)
                c_m3.metric("Fraud Rate", f"{fraud_rate:.2f}%")

                summary_rows = []
                for row in hist_data:
                    summary_rows.append({
                        "ID": row["id"],
                        "Class": "🚨 FRAUD" if row["predicted_class"] == 1 else "✅ Legit",
                        "Probability": f"{row['probability']:.4f}",
                        "Source": row["source"],
                        "Model Version": row["model_version"],
                        "Created At": row["created_at"],
                    })

                st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

                with st.expander("🔍 Inspect Full Feature Payload for a Specific Prediction"):
                    record_ids = [r["ID"] for r in summary_rows]
                    selected_id = st.selectbox("Select Prediction ID", record_ids)
                    chosen_rec = next((r for r in hist_data if r["id"] == selected_id), None)
                    if chosen_rec:
                        st.json({
                            "id": chosen_rec["id"],
                            "predicted_class": chosen_rec["predicted_class"],
                            "probability": chosen_rec["probability"],
                            "source": chosen_rec["source"],
                            "model_version": chosen_rec["model_version"],
                            "created_at": chosen_rec["created_at"],
                            "features": chosen_rec.get("features"),
                        })

                # Source distribution chart
                source_counts = pd.Series([h["source"] for h in hist_data]).value_counts()
                st.bar_chart(source_counts)
        else:
            st.error(f"Failed to fetch predictions history: {hist_resp.text}")
    except Exception as e:
        st.error(f"Error connecting to backend: {e}")
