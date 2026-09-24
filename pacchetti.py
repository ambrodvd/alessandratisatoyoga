"""Acquisto di un pacchetto di lezioni registrate."""

import streamlit as st

import data
import mailer

st.title("🎬 Acquista un pacchetto di lezioni registrate")

try:
    categories = data.load_categories()
    in_vendita = data.load_recording_packages()
except Exception:
    st.error("Impossibile caricare i pacchetti. Riprova tra un momento.")
    st.stop()

if categories.empty:
    st.info("Nessun pacchetto disponibile al momento.")
    st.stop()

pacchetti = categories[
    categories["category_id"].isin(in_vendita)
    & (categories["package_credits"] > 0)
    & (categories["price_package"] > 0)
]

if pacchetti.empty:
    st.info("Nessun pacchetto disponibile al momento.")
    st.stop()

# =============================================================
# SCELTA DEL PACCHETTO
# =============================================================


def etichetta(cid: str) -> str:
    r = pacchetti[pacchetti["category_id"] == cid].iloc[0]
    return (
        f"**{r['name']}** — {int(r['package_credits'])} lezioni registrate  ·  "
        f"_€ {r['price_package']:.2f}_"
    )


scelta = st.radio(
    "Scegli il pacchetto",
    options=list(pacchetti["category_id"]),
    format_func=etichetta,
    label_visibility="collapsed",
    key="scelta_pacchetto",
)
pack = pacchetti[pacchetti["category_id"] == scelta].iloc[0]

st.divider()

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

with st.form("package_form"):
    name = st.text_input(
        "Nome e cognome",
        placeholder="es. Maria Rossi",
        help="Servono entrambi, per esteso.",
    )
    email = st.text_input("Email")
    consent = st.checkbox(
        "Acconsento al trattamento dei miei dati per la gestione dell'acquisto."
    )
    submitted = st.form_submit_button("Acquista il pacchetto", type="primary")

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
        email_pulita = data.norm_email(email)
        prezzo = float(pack["price_package"])
        crediti = int(pack["package_credits"])
        base = st.secrets.get("paypal_me", "")
        pay_link = f"{base}/{prezzo:.2f}EUR" if base else ""

        try:
            data.add_package_request(email_pulita, nome_pulito, scelta)
        except Exception:
            pass  # la richiesta non blocca il pagamento

        st.success(
            f"Richiesta ricevuta — pacchetto {pack['name']}, "
            f"{crediti} lezioni registrate."
        )
        if pay_link:
            st.markdown(f"**€ {prezzo:.2f}** — [Paga con PayPal]({pay_link})")
        else:
            st.markdown(
                f"**€ {prezzo:.2f}** — ti scrivo a breve con le indicazioni "
                "per il pagamento."
            )
        st.caption(
            "Dopo il pagamento aggiorno io il tuo saldo, di solito entro poche ore."
        )

        try:
            mailer.send_package_purchase(
                to=email_pulita,
                name=nome_pulito,
                categoria=pack["name"],
                credits=crediti,
                price=prezzo,
                pay_link=pay_link,
            )
            st.caption(
                "Ti ho mandato una mail di riepilogo. Se non la trovi, "
                "controlla nello spam e segnala il messaggio come attendibile."
            )
        except Exception:
            st.warning(
                "La mail di riepilogo non è partita: usa il link qui sopra "
                "per il pagamento."
            )