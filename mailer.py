"""Invio email di conferma, cancellazione, ricevuta e lezione prova."""

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
    to: str,
    name: str,
    title: str,
    date_str: str,
    time_str: str,
    teacher: str,
    ref: str,
    payment_note: str = "",
    mode: str = "presenza",
    location: str = "",
    pay_link: str = "",
    prima_volta: bool = False,
) -> None:
    studio = _cfg()["studio_name"]

    if mode == "online":
        dove = (
            "La lezione è online. Ecco il link per collegarti:\n\n"
            f"  {location}\n\n"
            "Ti consiglio di entrare qualche minuto prima."
            if location.strip()
            else "La lezione è online. Ti mando il link a breve."
        )
    else:
        dove = (
            f"Ci vediamo qui: {location}"
            if location.strip()
            else "Ci vediamo in studio."
        )

    avviso_prova = (
        f"Se è la tua prima volta in {title} non procedere con il pagamento, "
        "in quanto hai diritto a una lezione di prova.\n\n"
        if prima_volta
        else ""
    )

    pagamento = f"Puoi pagare qui: {pay_link}\n\n" if pay_link else ""

    body = f"""Ciao {name},

il tuo posto per {title} di {date_str} alle {time_str} è confermato.

{dove}

{avviso_prova}{payment_note}{pagamento}Se non riesci a venire fammelo sapere rispondendo a questa mail.

A presto,
{studio}

--
Codice prenotazione: {ref}
"""
    _send(to, f"{title} — {date_str}, ore {time_str}", body)


def send_cancellation(
    to: str, name: str, title: str, date_str: str, time_str: str
) -> None:
    studio = _cfg()["studio_name"]
    body = f"""Ciao {name},

ho annullato la tua prenotazione per {title} del {date_str} alle {time_str}.

Se è stato un errore scrivimi per prenotare nuovamente.

{studio}
"""
    _send(to, f"Annullata — {title}, {date_str}", body)


def send_payment_receipt(
    to: str, name: str, categoria: str, credits: int,
    amount_eur: float, saldo: int, method: str = "",
) -> None:
    studio = _cfg()["studio_name"]

    parola = "lezione" if credits == 1 else "lezioni"
    metodo = f" via {method}" if method else ""

    if saldo > 0:
        residuo = f"Ora hai {saldo} ingressi disponibili per {categoria}."
    elif saldo == 0:
        residuo = f"Il tuo saldo per {categoria} è in pari."
    else:
        resta = abs(saldo)
        residuo = (
            f"Restano {resta} {'lezione' if resta == 1 else 'lezioni'} "
            f"da saldare per {categoria}."
        )

    body = f"""Ciao {name},

ho registrato il tuo pagamento di € {amount_eur:.2f}{metodo} per {credits} {parola} di {categoria}.

{residuo}

Grazie,
{studio}
"""
    _send(to, f"Pagamento registrato — {categoria}", body)


def send_trial_gift(
    to: str, name: str, categoria: str, date_str: str, time_str: str,
    price_single: float, price_package: float, package_credits: int,
    pay_base: str = "",
) -> None:
    studio = _cfg()["studio_name"]

    if pay_base and package_credits:
        offerta = (
            f"Se vorrai continuare puoi acquistare un pacchetto da "
            f"{package_credits} lezioni a € {price_package:.2f}:\n"
            f"  {pay_base}/{price_package:.2f}EUR\n\n"
            f"Oppure, se preferisci, puoi acquistare le lezioni di volta in volta "
            f"a € {price_single:.2f} l'una:\n"
            f"  {pay_base}/{price_single:.2f}EUR\n"
        )
    elif package_credits:
        offerta = (
            f"Se vorrai continuare puoi acquistare un pacchetto da "
            f"{package_credits} lezioni a € {price_package:.2f}, oppure le "
            f"lezioni di volta in volta a € {price_single:.2f} l'una.\n"
        )
    else:
        offerta = ""

    body = f"""Ciao {name},

benvenuta in {categoria}. Essendo la tua prima volta con me ho deciso di regalarti una lezione di prova:

  {categoria} — {date_str} alle {time_str}

{offerta}
Grazie per aver praticato con me,
{studio}
"""
    _send(to, "Grazie per aver praticato con me", body)