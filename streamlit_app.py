import streamlit as st

st.set_page_config(
    page_title="Alessandra Tisato Yoga",
    page_icon="🧘",
    layout="centered",
    initial_sidebar_state="collapsed",
)

prenota = st.Page("Prenota.py", title="Prenota", icon="🧘", default=True)
admin = st.Page("Admin.py", title="Gestione", icon="🔒")
pacchetti = st.Page(
    "pacchetti.py", title="Acquista un pacchetto di lezioni registrate", icon="🎬"
)

st.navigation([prenota, pacchetti, admin]).run()