from datetime import date

import streamlit as st

import data
import mailer

st.set_page_config(page_title="Admin", page_icon="🔒", layout="wide")
st.title("🔒 Gestione")

if "admin_ok" not in st.session_state:
    st.session_state.admin_ok = False

if not st.session_state.admin_ok:
    pw = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pw == st.secrets["admin_password"]:
            st.session_state.admin_ok = True
            st.rerun()
        else:
            st.error("Password errata.")
    st.stop()

if st.button("Aggiorna dati"):
    data.load_lessons.clear()
    data.load_bookings.clear()
    data.load_payments.clear()
    st.rerun()

lessons = data.load_lessons()
bookings = data.load_bookings()
payments = data.load_payments()

tab_saldi, tab_pren, tab_pag = st.tabs(["Saldi", "Prenotazioni", "Pagamenti"])

# --- saldi ---
with tab_saldi:
    balances = data.balances_all(payments, bookings)
    if balances.empty:
        st.info("Nessun dato.")
    else:
        debtors = balances[balances["saldo"] < 0]
        c1, c2 = st.columns(2)
        c1.metric("Persone con saldo negativo", len(debtors))
        c2.metric("Lezioni non saldate", int(-debtors["saldo"].sum()) if not debtors.empty else 0)

        if not debtors.empty:
            st.error("Da incassare")
            st.dataframe(debtors, use_container_width=True, hide_index=True)

        st.subheader("Tutti i saldi")
        st.dataframe(balances, use_container_width=True, hide_index=True)
        st.download_button(
            "Scarica saldi CSV",
            balances.to_csv(index=False).encode("utf-8"),
            file_name=f"saldi_{date.today().isoformat()}.csv",
            mime="text/csv",
        )

# --- prenotazioni ---
with tab_pren:
    if bookings.empty:
        st.info("Nessuna prenotazione.")
    else:
        merged = bookings.merge(lessons, on="lesson_id", how="left")
        merged = merged.sort_values(["date", "time", "timestamp"], na_position="last")
        active = merged[merged["status"] != "cancelled"]

        c1, c2, c3 = st.columns(3)
        c1.metric("Confermate", len(active))
        c2.metric("Annullate", len(merged) - len(active))
        c3.metric("Future", len(active[active["date"] >= date.today()]) if not active.empty else 0)

        st.dataframe(
            merged[["booking_id", "date", "time", "title", "name", "email",
                    "phone", "timestamp", "status"]],
            use_container_width=True, hide_index=True,
        )
        st.download_button(
            "Scarica prenotazioni CSV",
            merged.to_csv(index=False).encode("utf-8"),
            file_name=f"prenotazioni_{date.today().isoformat()}.csv",
            mime="text/csv",
        )

        st.subheader("Annulla una prenotazione")
        ref = st.text_input("Codice prenotazione")
        avvisa = st.checkbox("Invia email di annullamento", value=True)
        if st.button("Annulla", type="primary") and ref.strip():
            code = ref.strip().upper()
            row = merged[merged["booking_id"] == code]
            if data.cancel_booking(code):
                st.success(f"{code} annullata.")
                if avvisa and not row.empty:
                    r = row.iloc[0]
                    try:
                        mailer.send_cancellation(
                            to=r["email"], name=r["name"], title=r.get("title", ""),
                            date_str=r["date"].strftime("%d/%m/%Y") if r.get("date") else "",
                            time_str=r.get("time", ""),
                        )
                    except Exception:
                        st.warning("Annullata, ma l'email non è partita.")
                st.rerun()
            else:
                st.error("Codice non trovato.")

# --- pagamenti ---
with tab_pag:
    st.subheader("Registra un pagamento")
    with st.form("nuovo_pagamento"):
        c1, c2 = st.columns(2)
        p_email = c1.text_input("Email")
        p_name = c2.text_input("Nome")
        c3, c4, c5 = st.columns(3)
        p_credits = c3.number_input("Lezioni acquistate", min_value=1, value=10, step=1)
        p_amount = c4.number_input("Importo €", min_value=0.0, value=120.0, step=5.0)
        p_method = c5.selectbox("Metodo", ["PayPal", "Bonifico", "Contanti", "Altro"])
        p_date = st.date_input("Data pagamento", value=date.today())
        p_note = st.text_input("Nota (facoltativa)")
        ok = st.form_submit_button("Registra", type="primary")

    if ok:
        if "@" not in p_email:
            st.error("Email non valida.")
        else:
            pid = data.add_payment(
                email=p_email, name=p_name, credits=int(p_credits),
                amount_eur=float(p_amount), date_str=p_date.isoformat(),
                method=p_method, note=p_note,
            )
            saldo = data.balance_live(p_email)
            st.success(f"Pagamento {pid} registrato. Saldo attuale: {saldo} lezioni.")

    st.divider()
    if payments.empty:
        st.info("Nessun pagamento registrato.")
    else:
        st.metric("Incassato totale", f"€ {payments['amount_eur'].sum():,.2f}")
        st.dataframe(payments, use_container_width=True, hide_index=True)