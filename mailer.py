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
) -> None:
    studio = st.secrets["email"]["studio_name"]
    body = f"""Ciao {name},

la tua prenotazione è confermata.

  Lezione:    {title}
  Data:       {date_str}
  Ora:        {time_str}
  Insegnante: {teacher}

  Codice prenotazione: {ref}
{payment_note}
Se non puoi venire, avvisami rispondendo a questa email.

A presto,
{studio}
"""
    _send(to, f"Prenotazione confermata — {title}, {date_str}", body)


def send_cancellation(
    to: str, name: str, title: str, date_str: str, time_str: str
) -> None:
    studio = st.secrets["email"]["studio_name"]
    body = f"""Ciao {name},

la tua prenotazione per {title} del {date_str} alle {time_str} è stata annullata.

{studio}
"""
    _send(to, f"Prenotazione annullata — {title}, {date_str}", body)