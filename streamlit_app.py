import streamlit as st

st.set_page_config(
    page_title="Alessandra Tisato Yoga",
    page_icon="🧘",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# =============================================================
# STILE MOBILE
# =============================================================

st.markdown(
    """
    <style>
    /* meno spazio vuoto in alto, soprattutto su telefono */
    [data-testid="stMainBlockContainer"], .block-container {
        padding-top: 3.5rem;
        padding-bottom: 3rem;
    }

    /* lezioni e pacchetti come "card" grandi, facili da toccare */
    .st-key-scelta_lezione,
    .st-key-scelta_pacchetto {
        width: 100% !important;
    }
    .st-key-scelta_lezione [role="radiogroup"],
    .st-key-scelta_pacchetto [role="radiogroup"] {
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }
    .st-key-scelta_lezione [data-testid="stRadioOption"],
    .st-key-scelta_pacchetto [data-testid="stRadioOption"] {
        width: 100%;
        box-sizing: border-box;
        padding: 0.75rem 0.85rem;
        border: 1px solid rgba(128, 128, 128, 0.35);
        border-radius: 0.6rem;
        margin: 0;
        cursor: pointer;
    }
    .st-key-scelta_lezione [data-testid="stRadioOption"][data-selected="true"],
    .st-key-scelta_pacchetto [data-testid="stRadioOption"][data-selected="true"] {
        border-color: var(--primary-color, #ff4b4b);
        box-shadow: 0 0 0 1px var(--primary-color, #ff4b4b);
    }

    @media (max-width: 640px) {
        [data-testid="stMainBlockContainer"], .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        h1 {
            font-size: 1.6rem !important;
        }
        /* 16px evita lo zoom automatico di iOS quando si tocca un campo */
        input, textarea {
            font-size: 16px !important;
        }
        /* pulsanti più alti, comodi col pollice */
        .stButton button, .stFormSubmitButton button, .stLinkButton a {
            min-height: 3rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# =============================================================
# NAVIGAZIONE
# =============================================================

prenota = st.Page("Prenota.py", title="Prenota", icon="🧘", default=True)
admin = st.Page("Admin.py", title="Gestione", icon="🔒")
pacchetti = st.Page(
    "pacchetti.py", title="Lezioni registrate", icon="🎬"
)

# barra in alto su computer; su telefono Streamlit la raccoglie nel menu »
st.navigation([prenota, pacchetti, admin], position="top").run()
