from datetime import date, timedelta

import streamlit as st

import data
import mailer

st.title("🧘 Prenota una lezione")

try:
    lessons = data.load_lessons()
    bookings = data.load_bookings()
    categories = data.load_categories()
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

# =============================================================
# FILTRI
# =============================================================

c1, c2 = st.columns(2)

filtro = c1.selectbox(
    "Mostra",
    options=["questa_settimana", "prossima_settimana", "tutte", "presenza", "online"],
    format_func=lambda m: {
        "tutte": "Tutte le lezioni",
        "questa_settimana": "📅 Questa settimana",
        "prossima_settimana": "📅 Prossima settimana",
        "presenza": "📍 Solo in presenza",
        "online": "💻 Solo online",
    }[m],
    key="filtro_mostra",
)

ordine = c2.selectbox(
    "Ordina per",
    options=["data_asc", "data_desc"],
    format_func=lambda o: {
        "data_asc": "Data — prima le più vicine",
        "data_desc": "Data — prima le più lontane",
    }[o],
    key="filtro_ordine",
)

oggi = date.today()
domenica = oggi + timedelta(days=6 - oggi.weekday())

if filtro in ("presenza", "online"):
    vista = upcoming[upcoming["mode"] == filtro]
elif filtro == "questa_settimana":
    vista = upcoming[upcoming["date"] <= domenica]
elif filtro == "prossima_settimana":
    vista = upcoming[
        (upcoming["date"] > domenica)
        & (upcoming["date"] <= domenica + timedelta(days=7))
    ]
else:
    vista = upcoming

vista = vista.sort_values(["date", "time"], ascending=(ordine == "data_asc"))

if vista.empty:
    st.info("Nessuna lezione con questi filtri.")
    st.stop()

st.divider()

# =============================================================
# ELENCO LEZIONI
# =============================================================

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


slots = list(vista.itertuples(index=False))
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
        key="scelta_lezione",
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

# =============================================================
# VALIDAZIONE
# =============================================================


def nome_valido(valore: str) -> str:
    """Messaggio di errore, oppure stringa vuota se il nome va bene."""
    pulito = " ".join(str(valore or "").split())
    if not pulito:
        return "Inserisci nome e cognome."
    if not all(c.isalpha() or c in " '-." for c in pulito):
        return "Il nome può contenere solo lettere, apostrofi e trattini."
    parti = pulito.split(" ")
    if len(parti) < 2:
        return "Inserisci sia il nome che il cognome."
    if any(len(p.replace(".", "").replace("'", "").replace("-", "")) < 2 for p in parti):
        return "Scrivi nome e cognome per esteso, non le iniziali."
    return ""


# =============================================================
# FORM
# =============================================================

with st.form("booking_form"):
    name = st.text_input(
        "Nome e cognome",
        placeholder="es. Maria Rossi",
        help="Servono entrambi, per esteso.",
    )
    email = st.text_input("Email")
    consent = st.checkbox(
        "Acconsento al trattamento dei miei dati per la gestione della prenotazione."
    )
    submitted = st.form_submit_button("Conferma prenotazione", type="primary")

if submitted:
    errore_nome = nome_valido(name)
    if errore_nome:
        st.error(errore_nome)
    elif "@" not in email or "." not in email.split("@")[-1]:
        st.error("Inserisci un indirizzo email valido.")
    elif not consent:
        st.error("Devi accettare l'informativa per procedere.")
    else:
        nome_pulito = " ".join(name.split()).title()
        with st.spinner("Confermo..."):
            if data.already_booked(choice.lesson_id, email):
                st.warning("Risulti già iscritto a questa lezione.")
            elif data.count_live(choice.lesson_id) >= choice.capacity:
                st.error(
                    "Qualcuno ha appena preso l'ultimo posto. "
                    "Scegli un'altra lezione."
                )
                data.load_bookings.clear()
            else:
                cat_id = choice.category_id
                usate_prima = data.used_live(email, cat_id)
                balance_before = data.balance_live(email, cat_id)
                ref = data.add_booking(choice.lesson_id, nome_pulito, email)
                balance_after = balance_before - 1
                prima_volta = usate_prima == 0

                st.success(
                    f"Prenotato — {choice.title} il "
                    f"{choice.date.strftime('%d/%m/%Y')} alle {choice.time}.\n\n"
                    f"Codice: **{ref}**"
                )

                if balance_after < 0:
                    da_pagare = abs(balance_after)
                    base = st.secrets.get("paypal_me", "")

                    prezzo_singola = prezzo_pacchetto = 0.0
                    crediti_pacchetto = 0
                    if not categories.empty and cat_id:
                        match = categories[categories["category_id"] == cat_id]
                        if not match.empty:
                            c = match.iloc[0]
                            prezzo_singola = float(c["price_single"])
                            prezzo_pacchetto = float(c["price_package"])
                            crediti_pacchetto = int(c["package_credits"])

                    importo = prezzo_singola * da_pagare
                    parola = "lezione" if da_pagare == 1 else "lezioni"

                    if prima_volta:
                        st.info(
                            f"🎁 **Se è la tua prima volta in {choice.title} "
                            "hai diritto a una lezione di prova. "
                            "Non procedere con il pagamento.**"
                        )

                    st.warning(
                        f"Risulta **{da_pagare} {parola} da saldare** "
                        f"per {choice.title}."
                    )

                    if base:
                        col_a, col_b = st.columns(2)
                        with col_a:
                            st.markdown("**Salda il dovuto**")
                            st.markdown(
                                f"{da_pagare} × € {prezzo_singola:.2f} = "
                                f"**€ {importo:.2f}**"
                            )
                            st.markdown(
                                f"[Paga con PayPal]({base}/{importo:.2f}EUR)"
                            )
                        with col_b:
                            if crediti_pacchetto:
                                st.markdown("**Compra un pacchetto**")
                                st.markdown(
                                    f"{crediti_pacchetto} lezioni = "
                                    f"**€ {prezzo_pacchetto:.2f}**"
                                )
                                st.markdown(
                                    f"[Paga con PayPal]"
                                    f"({base}/{prezzo_pacchetto:.2f}EUR)"
                                )
                        st.caption(
                            "Dopo il pagamento aggiorno io il tuo saldo, "
                            "di solito entro poche ore."
                        )

                    avviso = (
                        f"Se è la tua prima volta in {choice.title} non procedere "
                        "con il pagamento, in quanto hai diritto a una lezione "
                        "di prova.\n\n"
                        if prima_volta
                        else ""
                    )

                    if base:
                        righe = [
                            f"Per {choice.title} risulta {da_pagare} {parola} da "
                            f"saldare.\n",
                            f"  Salda {da_pagare} {parola} — € {importo:.2f}",
                            f"  {base}/{importo:.2f}EUR\n",
                        ]
                        if crediti_pacchetto:
                            righe += [
                                f"  Oppure un pacchetto da {crediti_pacchetto} "
                                f"lezioni — € {prezzo_pacchetto:.2f}",
                                f"  {base}/{prezzo_pacchetto:.2f}EUR\n",
                            ]
                        nota = avviso + "\n".join(righe) + "\n"
                    else:
                        nota = avviso + (
                            f"Per {choice.title} risulta {da_pagare} {parola} da "
                            f"saldare (€ {importo:.2f}).\n\n"
                        )
                    pay_link = ""
                else:
                    st.info(
                        f"Ingressi residui per {choice.title}: **{balance_after}**"
                    )
                    nota = (
                        f"Dopo questa lezione ti restano {balance_after} "
                        f"ingressi per {choice.title}.\n\n"
                    )
                    pay_link = ""
                    st.balloons()

                try:
                    mailer.send_confirmation(
                        to=email,
                        name=nome_pulito,
                        title=choice.title,
                        date_str=choice.date.strftime("%d/%m/%Y"),
                        time_str=choice.time,
                        teacher=choice.teacher,
                        ref=ref,
                        payment_note=nota,
                        mode=choice.mode,
                        location=choice.location,
                        pay_link=pay_link,
                        prima_volta=False,
                    )
                    st.caption(
                        "Ti ho mandato una mail di conferma. Se non la trovi, "
                        "controlla nello spam e segnala il messaggio come attendibile."
                    )
                except Exception:
                    st.warning(
                        "Prenotazione registrata, ma l'email di conferma non è "
                        f"partita. Conserva il codice {ref}."
                    )