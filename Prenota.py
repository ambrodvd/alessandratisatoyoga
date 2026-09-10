from datetime import date, timedelta

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

upcoming = lessons[lessons["date"] >= date.today()]
if upcoming.empty:
    st.info("Nessuna lezione in programma.")
    st.stop()

taken = data.seats_taken(bookings)
upcoming = upcoming.assign(
    booked=lambda d: d["lesson_id"].map(taken).fillna(0).astype(int)
)
upcoming = upcoming.assign(free=lambda d: (d["capacity"] - d["booked"]).clip(lower=0))

# --- filtri ---

c1, c2 = st.columns(2)

filtro_modo = c1.selectbox(
    "Mostra",
    options=["tutte", "questa_settimana", "prossima_settimana", "presenza", "online"],
    format_func=lambda m: {
        "tutte": "Tutte le lezioni",
        "questa_settimana": "📅 Questa settimana",
        "prossima_settimana": "📅 Prossima settimana",
        "presenza": "📍 Solo in presenza",
        "online": "💻 Solo online",
    }[m],
)

ordine = c2.selectbox(
    "Ordina per",
    options=["data_asc", "data_desc"],
    format_func=lambda o: {
        "data_asc": "Data — prima le più vicine",
        "data_desc": "Data — prima le più lontane",
    }[o],
)

oggi = date.today()
lunedi = oggi - timedelta(days=oggi.weekday())
domenica = lunedi + timedelta(days=6)

if filtro_modo in ("presenza", "online"):
    vista = upcoming[upcoming["mode"] == filtro_modo]
elif filtro_modo == "questa_settimana":
    vista = upcoming[upcoming["date"] <= domenica]
elif filtro_modo == "prossima_settimana":
    vista = upcoming[
        (upcoming["date"] > domenica) & (upcoming["date"] <= domenica + timedelta(days=7))
    ]
else:
    vista = upcoming

vista = vista.sort_values(["date", "time"], ascending=(ordine == "data_asc"))

st.divider()

# --- elenco lezioni ---

GIORNI = {
    0: "lunedì", 1: "martedì", 2: "mercoledì", 3: "giovedì",
    4: "venerdì", 5: "sabato", 6: "domenica",
}


def etichetta(row) -> str:
    giorno = GIORNI[row.date.weekday()]
    icona = "💻 online" if row.mode == "online" else "📍 in presenza"
    stato = f"{row.free} posti" if row.free > 0 else "completo"
    return (
        f"**{row.title}** — {giorno} {row.date.strftime('%d/%m/%Y')} — "
        f"{icona} — ore {row.time}  ·  _{stato}_"
    )


slots = [r for r in vista.itertuples(index=False)]
disponibili = [r for r in slots if r.free > 0]
piene = [r for r in slots if r.free <= 0]

st.caption(f"{len(disponibili)} lezioni disponibili")

choice = None
if disponibili:
    choice = st.radio(
        "Scegli la lezione",
        options=disponibili,
        format_func=etichetta,
        label_visibility="collapsed",
    )

if piene:
    with st.expander(f"Lezioni complete ({len(piene)})"):
        for r in piene:
            st.markdown(etichetta(r))

if choice is None:
    st.warning("Tutte le lezioni sono complete al momento.")
    st.stop()

st.divider()

if choice.mode == "online":
    st.info("💻 Riceverai il link per collegarti nella mail di conferma.")
elif choice.location:
    st.info(f"📍 {choice.location}")

# --- form ---

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
                cat_id = choice.category_id
                balance_before = data.balance_live(email, cat_id)
                ref = data.add_booking(choice.lesson_id, name, email)
                balance_after = balance_before - 1

                st.success(
                    f"Prenotato — {choice.title} il "
                    f"{choice.date.strftime('%d/%m/%Y')} alle {choice.time}.\n\n"
                    f"Codice: **{ref}**"
                )

                if balance_after < 0:
                    da_pagare = abs(balance_after)
                    st.warning(
                        f"Risultano **{da_pagare} lezioni da saldare** "
                        f"per {choice.title}. Ti contatterò per il pagamento."
                    )
                    nota = (
                        f"Per {choice.title} risultano {da_pagare} lezioni da "
                        "saldare, ti scrivo a parte per il pagamento.\n\n"
                    )
                else:
                    st.info(f"Ingressi residui per {choice.title}: **{balance_after}**")
                    nota = (
                        f"Dopo questa lezione ti restano {balance_after} "
                        f"ingressi per {choice.title}.\n\n"
                    )
                    st.balloons()

                try:
                    mailer.send_confirmation(
                        to=email, name=name.strip(), title=choice.title,
                        date_str=choice.date.strftime("%d/%m/%Y"),
                        time_str=choice.time, teacher=choice.teacher,
                        ref=ref, payment_note=nota,
                        mode=choice.mode, location=choice.location,
                    )
                    st.caption(
                        "Ti ho mandato una mail di conferma. Se non la trovi, "
                        "controlla nello spam e segnala il messaggio come attendibile."
                    )
                except Exception as exc:
                    st.warning(
                        "Prenotazione registrata, ma l'email di conferma non è partita. "
                        f"Conserva il codice {ref}."
                    )
                    st.caption(f"Debug: {type(exc).__name__} — {exc}")