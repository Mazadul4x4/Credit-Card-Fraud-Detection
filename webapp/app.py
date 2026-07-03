import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Credit Card Fraud Detection",
    page_icon="💳",
    layout="centered"
)

st.title("💳 Credit Card Fraud Detection")

# -----------------------------------
# Backend Health
# -----------------------------------

st.subheader("Backend Status")

try:
    health = requests.get(f"{API_URL}/health")

    if health.status_code == 200:
        st.success("Backend Connected")
        st.json(health.json())
    else:
        st.error("Backend Error")

except Exception:
    st.error("Cannot connect to FastAPI")
    st.stop()

st.divider()

# -----------------------------------
# Prediction Form
# -----------------------------------

st.subheader("Create Prediction")

predicted_class = st.selectbox(
    "Predicted Class",
    [0, 1],
    help="0 = Legitimate, 1 = Fraud"
)

probability = st.slider(
    "Probability",
    0.0,
    1.0,
    0.50,
    0.001
)

source = st.text_input(
    "Source",
    value="streamlit"
)

if st.button("Predict"):

    payload = {
        "predicted_class": predicted_class,
        "probability": probability,
        "source": source
    }

    try:

        response = requests.post(
            f"{API_URL}/predict",
            json=payload
        )

        if response.status_code == 200:

            st.success("Prediction Saved Successfully!")

            st.json(response.json())

        else:

            st.error("Prediction Failed")

            st.write(response.text)

    except Exception as e:

        st.error(str(e))
        
st.divider()

st.subheader("Prediction History")

if st.button("Load Prediction History"):

    try:

        response = requests.get(f"{API_URL}/predictions")

        if response.status_code == 200:

            data = response.json()

            st.success(f"Loaded {len(data)} predictions")

            st.dataframe(data, use_container_width=True)

        else:

            st.error("Unable to load prediction history")

    except Exception as e:

        st.error(str(e))