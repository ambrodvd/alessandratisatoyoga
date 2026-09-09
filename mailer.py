"""Invio email di conferma e cancellazione."""

import smtplib
from email.message import EmailMessage

import streamlit as st


def _cfg() -> dict:
    """Legge e valida la configurazione email dai secrets."""
    try:
        cfg = dict(st.secrets["email"])
    except KeyError:
        raise RuntimeError(
            "Configurazione email assente: manca la sezione [email] nei secrets."
        )
    mancanti = [k for k in ("sender", "app_password", "studio_name") if not cfg.get(k)]
    if mancanti:
        raise RuntimeError(f"Configurazione email incompleta: {', '.join(mancanti)}")
    return cfg


def _send(to: str, subject: str, body: str) -> None:
    cfg = _cfg()
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
    studio = _cfg()["studio_name"]

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

ti confermo la tua prenotazione per la lezione {title} del {date_str} alle {time_str}.

{dove}

{payment_note}
Se poi non riesci a venire scrivimi rispondendo qui, cosi' libero il posto per qualcun altro.

A presto,
{studio}
"""
    _send(to, f"La tua lezione è confermata", body)


def send_cancellation(
    to: str, name: str, title: str, date_str: str, time_str: str
) -> None:
    studio = _cfg()["studio_name"]
    body = f"""Ciao {name},

la tua prenotazione per {title} del {date_str} alle {time_str} e' stata annullata.

{studio}
"""
    _send(to, f"Prenotazione annullata - {title}, {date_str}", body)