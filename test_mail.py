import traceback

import streamlit as st

import mailer

st.title("Test invio email")

cfg_ok = "email" in st.secrets
st.write("Blocco [email] nei secrets:", "trovato" if cfg_ok else "MANCANTE")

if cfg_ok:
    st.write("sender:", st.secrets["email"].get("sender", "— assente —"))
    pw = st.secrets["email"].get("app_password", "")
    st.write("app_password:", f"{len(pw)} caratteri" if pw else "— assente —")
    st.write("studio_name:", st.secrets["email"].get("studio_name", "— assente —"))

dest = st.text_input("Invia una mail di prova a", value="")

if st.button("Invia", type="primary") and dest:
    try:
        mailer.send_confirmation(
            to=dest, name="Prova", title="Lezione di test",
            date_str="01/01/2027", time_str="18:30",
            teacher="Alessandra", ref="TEST1234",
        )
        st.success("Inviata. Controlla la casella, anche lo spam.")
    except Exception:
        st.error("Fallito. Traceback qui sotto:")
        st.code(traceback.format_exc())