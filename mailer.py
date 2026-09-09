"""Invio email di conferma e cancellazione."""

import smtplib
from email.message import EmailMessage

import streamlit as st


def _send(to: str, subject: str, body: str) -> None:
    cfg = st.secrets["email"]
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{cfg['studio_name']} <{cfg['sender']}>"
    msg["To"] = to
    msg["Reply-To"] = cfg.get("reply_to", cfg["sender"])
    msg.set_content(body)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
        smtp.login(cfg["sender"], cfg["app_password"])
        smtp.send_message(msg)


def send_confirmation(
    to: str, name: str, title: str, date_str: str, time_str: str,
    teacher: str, ref: str, payment_note: str = "",
    mode: str = "presenza", location: str = "",
) -> None:
    studio = st.secrets["email"]["studio_name"]

    if mode == "online":
        dove = (
            "La lezione e' online. Ecco il link per collegarti:\n\n"
            f"  {location}\n\n"
            "Ti consiglio di entrare qualche minuto prima."
            if location.strip()
            else "La lezione e' online. Ti mando il link a breve."
        )
    else:
        dove = (
            f"Ci vediamo qui: {location}"
            if location.strip()
            else "Ci vediamo in studio."
        )

    body = f"""Ciao {name},

ti confermo il posto per {title} di {date_str} alle {time_str}, con {teacher}.

{dove}

Il codice della tua prenotazione e' {ref}.
{payment_note}
Se poi non riesci a venire scrivimi rispondendo qui, cosi' libero il posto per qualcun altro.

A presto,
{studio}
"""
    _send(to, f"Ci vediamo {date_str} — {title}", body)


def send_cancellation(
    to: str, name: str, title: str, date_str: str, time_str: str
) -> None:
    studio = st.secrets["email"]["studio_name"]
    body = f"""Ciao {name},

la tua prenotazione per {title} del {date_str} alle {time_str} è stata annullata.

{studio}
"""
    _send(to, f"Prenotazione annullata — {title}, {date_str}", body)