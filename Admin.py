from datetime import date

import streamlit as st

import data
import mailer
from datetime import date, time, timedelta
import pandas as pd

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

tab_lezioni, tab_saldi, tab_pren, tab_pag = st.tabs(["Lezioni", "Saldi", "Prenotazioni", "Pagamenti"])

# --- lezioni ---
with tab_lezioni:
    st.subheader("Aggiungi lezioni")

    titoli_noti = sorted(lessons["title"].unique()) if not lessons.empty else []
    docenti_noti = sorted(lessons["teacher"].unique()) if not lessons.empty else []

    l_mode = st.radio(
        "Tipo di lezione",
        options=["presenza", "online"],
        format_func=lambda m: "📍 In presenza" if m == "presenza" else "💻 Online",
        horizontal=True,
        key="modo_lezione",
    )

    with st.form("nuova_lezione"):
        c1, c2 = st.columns(2)
        l_title = c1.text_input(
            "Titolo",
            value=titoli_noti[0] if titoli_noti else "",
            help="es. Vinyasa Flow",
        )
        l_teacher = c2.text_input(
            "Insegnante", value=docenti_noti[0] if docenti_noti else ""
        )

        if l_mode == "online":
            luoghi_noti = (
                sorted(
                    lessons.loc[lessons["mode"] == "online", "location"]
                    .replace("", pd.NA).dropna().unique()
                )
                if not lessons.empty else []
            )
            l_location = st.text_input(
                "Link Zoom",
                value=luoghi_noti[-1] if luoghi_noti else "",
                placeholder="https://zoom.us/j/...",
                help="Verrà inviato nella mail di conferma.",
            )
        else:
            luoghi_noti = (
                sorted(
                    lessons.loc[lessons["mode"] != "online", "location"]
                    .replace("", pd.NA).dropna().unique()
                )
                if not lessons.empty else []
            )
            l_location = st.text_input(
                "Luogo",
                value=luoghi_noti[-1] if luoghi_noti else "",
                placeholder="Via Roma 12, Milano",
            )

        c3, c4, c5 = st.columns(3)
        l_date = c3.date_input("Data", value=date.today() + timedelta(days=1))
        l_time = c4.time_input("Ora", value=time(18, 30), step=timedelta(minutes=15))
        l_capacity = c5.number_input("Posti", min_value=1, max_value=100, value=12)

        st.markdown("**Ripeti** — lascia a 1 per una lezione singola")
        c6, c7 = st.columns(2)
        ripetizioni = c6.number_input(
            "Numero di settimane", min_value=1, max_value=52, value=1
        )
        c7.caption("Crea la stessa lezione ogni settimana, stesso giorno e ora.")

        crea = st.form_submit_button("Crea", type="primary")

    if crea:
        if not l_title.strip():
            st.error("Il titolo è obbligatorio.")
        elif l_mode == "online" and not l_location.strip().startswith("http"):
            st.error("Per le lezioni online serve un link valido (deve iniziare con http).")
        else:
            creati, errori = [], []
            for i in range(int(ripetizioni)):
                giorno = l_date + timedelta(weeks=i)
                try:
                    lid = data.add_lesson(
                        date_str=giorno.isoformat(),
                        time_str=l_time.strftime("%H:%M"),
                        title=l_title,
                        teacher=l_teacher,
                        capacity=int(l_capacity),
                        mode=l_mode,
                        location=l_location,
                    )
                    creati.append(f"{lid} — {giorno.strftime('%d/%m/%Y')}")
                except Exception as exc:
                    errori.append(f"{giorno.strftime('%d/%m/%Y')}: {exc}")

            if creati:
                st.success(f"Create {len(creati)} lezioni.")
                st.write("\n".join(f"- {c}" for c in creati))
            if errori:
                st.error("Alcune non sono state create:")
                st.write("\n".join(f"- {e}" for e in errori))
            data.load_lessons.clear()

    st.divider()
    st.subheader("Calendario")

    if lessons.empty:
        st.info("Nessuna lezione in calendario.")
    else:
        solo_future = st.checkbox("Mostra solo le future", value=True)
        vista = lessons[lessons["date"] >= date.today()] if solo_future else lessons
        vista = vista.sort_values(["date", "time"])

        if vista.empty:
            st.info("Nessuna lezione futura.")
        else:
            taken = data.seats_taken(bookings)
            vista = vista.assign(
                prenotati=lambda d: d["lesson_id"].map(taken).fillna(0).astype(int)
            )
            vista = vista.assign(
                liberi=lambda d: (d["capacity"] - d["prenotati"]).clip(lower=0)
            )
            st.dataframe(
                vista[["lesson_id", "date", "time", "title", "teacher", "mode",
                       "location", "capacity", "prenotati", "liberi"]],
                use_container_width=True, hide_index=True,
            )

            st.subheader("Elimina una lezione")
            st.caption(
                "Elimina la riga dal calendario. Le prenotazioni già registrate "
                "restano nel foglio ma perdono il collegamento: annullale prima."
            )
            da_eliminare = st.selectbox(
                "Lezione",
                options=list(vista["lesson_id"]),
                format_func=lambda lid: (
                    lambda r: f"{lid} · {r['date'].strftime('%d/%m/%Y')} {r['time']} · "
                              f"{r['title']} ({r['prenotati']} prenotati)"
                )(vista[vista["lesson_id"] == lid].iloc[0]),
            )
            conferma = st.checkbox("Confermo l'eliminazione")
            if st.button("Elimina lezione") and conferma:
                if data.delete_lesson(da_eliminare):
                    st.success(f"{da_eliminare} eliminata.")
                    st.rerun()
                else:
                    st.error("Lezione non trovata.")

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