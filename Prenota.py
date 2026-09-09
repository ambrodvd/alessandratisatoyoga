from datetime import date

import streamlit as st

import data
import mailer

st.set_page_config(page_title="Prenota una lezione", page_icon="🧘", layout="centered")
st.title("🧘 Prenota una lezione")

try:
    lessons = data.load_lessons()
    bookings = data.load_bookings()
except Exception:
    st.error("Impossibile caricare il calendario. Riprova tra un momento.")
    st.stop()

if lessons.empty:
    st.info("Nessuna lezione in programma.")
    st.stop()

upcoming = lessons[lessons["date"] >= date.today()].sort_values(["date", "time"])
if upcoming.empty:
    st.info("Nessuna lezione in programma.")
    st.stop()

taken = data.seats_taken(bookings)
upcoming = upcoming.assign(
    booked=lambda d: d["lesson_id"].map(taken).fillna(0).astype(int)
)
upcoming = upcoming.assign(free=lambda d: (d["capacity"] - d["booked"]).clip(lower=0))

chosen_date = st.selectbox(
    "Data",
    options=sorted(upcoming["date"].unique()),
    format_func=lambda d: d.strftime("%A %d %B %Y"),
)

day = upcoming[upcoming["date"] == chosen_date]
slots = list(day.itertuples(index=False))


def slot_label(row) -> str:
    tail = f"{row.free} posti liberi" if row.free > 0 else "COMPLETO"
    icona = "💻" if row.mode == "online" else "📍"
    return f"{row.time} · {icona} {row.title} · {row.teacher} — {tail}"


choice = st.radio("Lezione", options=slots, format_func=slot_label)
st.divider()

if choice.mode == "online":
    st.info("💻 Lezione online — riceverai il link Zoom nella mail di conferma.")
elif choice.location:
    st.info(f"📍 {choice.location}")

if choice.free <= 0:
    st.error("Questa lezione è completa. Scegline un'altra.")
    st.stop()

with st.form("booking_form"):
    name = st.text_input("Nome e cognome")
    email = st.text_input("Email")
    consent = st.checkbox(
        "Acconsento al trattamento dei miei dati per la gestione della prenotazione."
    )
    submitted = st.form_submit_button("Conferma prenotazione", type="primary")

if submitted:
    if not name.strip():
        st.error("Inserisci il tuo nome.")
    elif "@" not in email or "." not in email.split("@")[-1]:
        st.error("Inserisci un indirizzo email valido.")
    elif not consent:
        st.error("Devi accettare l'informativa per procedere.")
    else:
        with st.spinner("Confermo..."):
            if data.already_booked(choice.lesson_id, email):
                st.warning("Risulti già iscritto a questa lezione.")
            elif data.count_live(choice.lesson_id) >= choice.capacity:
                st.error("Qualcuno ha appena preso l'ultimo posto. Scegli un'altra lezione.")
                data.load_bookings.clear()
            else:
                balance_before = data.balance_live(email)
                ref = data.add_booking(choice.lesson_id, name, email)
                balance_after = balance_before - 1

                st.success(
                    f"Prenotato — {choice.title} il "
                    f"{chosen_date.strftime('%d/%m/%Y')} alle {choice.time}.\n\n"
                    f"Codice: **{ref}**"
                )
                st.caption(
                    "Ti ho mandato una mail di conferma. "
                    "Se non la trovi, controlla nello spam e segnala "
                    "il messaggio come attendibile."
                )

                if balance_after < 0:
                    da_pagare = abs(balance_after)
                    st.warning(
                        f"Risultano **{da_pagare} lezioni da saldare**. "
                        "Ti contatterò per il pagamento."
                    )
                    nota = (
                        f"\n  ⚠ Lezioni da saldare: {da_pagare}\n"
                    )
                else:
                    st.info(f"Crediti residui dopo questa lezione: **{balance_after}**")
                    nota = f"\n  Crediti residui: {balance_after}\n"
                    st.balloons()

                try:
                    mailer.send_confirmation(
                        to=email, name=name.strip(), title=choice.title,
                        date_str=chosen_date.strftime("%d/%m/%Y"),
                        time_str=choice.time, teacher=choice.teacher,
                        ref=ref, payment_note=nota,
                        mode=choice.mode, location=choice.location,
                    )
                except Exception:
                    import traceback
                    st.warning("Prenotazione registrata, ma l'email non è partita.")
                    st.code(traceback.format_exc())