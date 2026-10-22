from datetime import date, timedelta

import pandas as pd
import streamlit as st

import api_client

st.title("📜 Past predictions")

c1, c2, c3 = st.columns(3)
start_date = c1.date_input("Start date", value=date.today() - timedelta(days=7))
end_date = c2.date_input("End date", value=date.today())
source_label = c3.selectbox("Prediction source", ["All", "Webapp", "Scheduled predictions"])
source = {"All": "all", "Webapp": "webapp", "Scheduled predictions": "scheduled"}[source_label]

if st.button("Search", type="primary"):
    if start_date > end_date:
        st.error("Start date must be before end date.")
        st.stop()
    try:
        response = api_client.past_predictions(start_date, end_date, source)
    except api_client.ApiError as exc:
        st.error(str(exc))
        st.stop()

    if response["count"] == 0:
        st.info("No predictions for these filters.")
    else:
        rows = []
        for p in response["predictions"]:
            rows.append(
                {
                    "id": p["id"],
                    "created_at": p["created_at"],
                    "source": p["source"],
                    "model_version": p["model_version"],
                    "transaction_id": p["transaction_id"],
                    "prediction": "fraud" if p["prediction"] == 1 else "legit",
                    "fraud_probability": round(p["fraud_probability"], 4),
                    **p["features"],
                }
            )
        df = pd.DataFrame(rows)
        st.write(f"{len(df)} predictions")
        st.dataframe(df, use_container_width=True, hide_index=True)
