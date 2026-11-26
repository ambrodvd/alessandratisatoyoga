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

    /* il pannello "schermata Home" viene creato per primo ma mostrato in fondo,
       così compare anche quando la pagina si ferma prima (st.stop) */
    div:has(> .st-key-installa_app) {
        order: 9999;
        margin-top: 1.5rem;
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
pagina = st.navigation([prenota, pacchetti, admin], position="top")

# =============================================================
# ISTRUZIONI SCHERMATA HOME (in fondo alla pagina Prenota)
# =============================================================

if pagina.title == "Prenota":
    with st.container(key="installa_app"):
        with st.expander("📲 Aggiungi l'app alla schermata Home"):
            st.markdown(
                "Se hai aperto il link da WhatsApp, Instagram o dalla mail, "
                "aprilo prima nel browser (Safari su iPhone, Chrome su Android).\n\n"
                "**iPhone (Safari):** tocca Condividi ⬆️ (su iOS 26 è dentro il "
                "menu ⋯ accanto all'indirizzo), scorri e tocca "
                "**Aggiungi alla schermata Home**, poi **Aggiungi**.\n\n"
                "**Android (Chrome):** tocca il menu ⋮ in alto a destra e scorri "
                "fino a **Installa e crea scorciatoia** (su alcuni telefoni si "
                "chiama *Aggiungi a schermata Home*). Nella finestra che si apre "
                "scegli **Crea scorciatoia**, non «Installa», scrivi un nome, "
                "per esempio *Yoga Alessandra*, e conferma.\n\n"
                "Da quel momento trovi le lezioni con un tocco, come un'app."
            )

pagina.run()
