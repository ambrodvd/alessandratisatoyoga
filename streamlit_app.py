import streamlit as st

prenota = st.Page("Prenota.py", title="Prenota", icon="🧘", default=True)
admin = st.Page("Admin.py", title="Gestione", icon="🔒")

st.navigation([prenota, admin]).run()