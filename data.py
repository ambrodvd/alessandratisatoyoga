"""Data access layer. Google Sheets."""

import uuid
from datetime import datetime

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

BOOKING_COLUMNS = [
    "booking_id", "lesson_id", "name", "email",
    "phone", "timestamp", "status",
]

PAYMENT_COLUMNS = [
    "payment_id", "email", "name", "credits",
    "amount_eur", "date", "method", "note",
]


def norm_email(value: str) -> str:
    return str(value or "").strip().lower()


@st.cache_resource(show_spinner=False)
def _client() -> gspread.Client:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)


def _sheet(tab: str) -> gspread.Worksheet:
    return _client().open_by_key(st.secrets["spreadsheet_id"]).worksheet(tab)


# --- lessons ----------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def load_lessons() -> pd.DataFrame:
    df = pd.DataFrame(_sheet("lessons").get_all_records())
    if df.empty:
        return pd.DataFrame(
            columns=["lesson_id", "date", "time", "title", "teacher",
                     "capacity", "mode", "location"]
        )
    df["lesson_id"] = df["lesson_id"].astype(str)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["time"] = df["time"].astype(str)
    df["capacity"] = pd.to_numeric(df["capacity"], errors="coerce").fillna(0).astype(int)
    if "mode" not in df.columns:
        df["mode"] = "presenza"
    df["mode"] = (
        df["mode"].astype(str).str.strip().str.lower()
        .replace("", "presenza").fillna("presenza")
    )
    if "location" not in df.columns:
        df["location"] = ""
    df["location"] = df["location"].astype(str).fillna("")
    return df.dropna(subset=["date"])


def add_lesson(
    date_str: str, time_str: str, title: str, teacher: str,
    capacity: int, mode: str = "presenza", location: str = "",
) -> str:
    lesson_id = next_lesson_id()
    _sheet("lessons").append_row(
        [
            lesson_id, date_str, time_str, title.strip(), teacher.strip(),
            int(capacity), mode.strip().lower(), location.strip(),
        ],
        value_input_option="USER_ENTERED",
    )
    load_lessons.clear()
    return lesson_id

def next_lesson_id() -> str:
    """Genera L001, L002... leggendo direttamente dal foglio."""
    records = _sheet("lessons").get_all_records()
    nums = []
    for r in records:
        val = str(r.get("lesson_id", "")).strip().upper()
        if val.startswith("L") and val[1:].isdigit():
            nums.append(int(val[1:]))
    return f"L{(max(nums) + 1) if nums else 1:03d}"


def delete_lesson(lesson_id: str) -> bool:
    ws = _sheet("lessons")
    cell = ws.find(str(lesson_id))
    if cell is None or cell.col != 1:
        return False
    ws.delete_rows(cell.row)
    load_lessons.clear()
    return True

# --- bookings ---------------------------------------------------------------

@st.cache_data(ttl=20, show_spinner=False)
def load_bookings() -> pd.DataFrame:
    df = pd.DataFrame(_sheet("bookings").get_all_records())
    if df.empty:
        return pd.DataFrame(columns=BOOKING_COLUMNS)
    df["lesson_id"] = df["lesson_id"].astype(str)
    df["email"] = df["email"].map(norm_email)
    if "status" not in df.columns:
        df["status"] = "confirmed"
    df["status"] = df["status"].replace("", "confirmed").fillna("confirmed")
    return df


def seats_taken(bookings: pd.DataFrame) -> pd.Series:
    if bookings.empty:
        return pd.Series(dtype=int)
    active = bookings[bookings["status"] != "cancelled"]
    if active.empty:
        return pd.Series(dtype=int)
    return active.groupby("lesson_id").size()


def count_live(lesson_id: str) -> int:
    records = _sheet("bookings").get_all_records()
    return sum(
        1 for r in records
        if str(r.get("lesson_id")) == str(lesson_id)
        and (r.get("status") or "confirmed") != "cancelled"
    )


def already_booked(lesson_id: str, email: str) -> bool:
    records = _sheet("bookings").get_all_records()
    target = norm_email(email)
    return any(
        str(r.get("lesson_id")) == str(lesson_id)
        and norm_email(r.get("email")) == target
        and (r.get("status") or "confirmed") != "cancelled"
        for r in records
    )


def add_booking(lesson_id: str, name: str, email: str, phone: str = "") -> str:
    booking_id = uuid.uuid4().hex[:8].upper()
    _sheet("bookings").append_row(
        [
            booking_id, str(lesson_id), name.strip(), norm_email(email),
            phone.strip(), datetime.now().isoformat(timespec="seconds"), "confirmed",
        ],
        value_input_option="USER_ENTERED",
    )
    load_bookings.clear()
    return booking_id


def cancel_booking(booking_id: str) -> bool:
    ws = _sheet("bookings")
    cell = ws.find(str(booking_id))
    if cell is None or cell.col != 1:
        return False
    ws.update_cell(cell.row, BOOKING_COLUMNS.index("status") + 1, "cancelled")
    load_bookings.clear()
    return True


# --- payments ---------------------------------------------------------------

@st.cache_data(ttl=60, show_spinner=False)
def load_payments() -> pd.DataFrame:
    df = pd.DataFrame(_sheet("payments").get_all_records())
    if df.empty:
        return pd.DataFrame(columns=PAYMENT_COLUMNS)
    df["email"] = df["email"].map(norm_email)
    df["credits"] = pd.to_numeric(df["credits"], errors="coerce").fillna(0).astype(int)
    df["amount_eur"] = pd.to_numeric(df["amount_eur"], errors="coerce").fillna(0.0)
    return df


def add_payment(
    email: str, name: str, credits: int, amount_eur: float,
    date_str: str, method: str, note: str = "",
) -> str:
    payment_id = "P" + uuid.uuid4().hex[:6].upper()
    _sheet("payments").append_row(
        [
            payment_id, norm_email(email), name.strip(), int(credits),
            float(amount_eur), date_str, method.strip(), note.strip(),
        ],
        value_input_option="USER_ENTERED",
    )
    load_payments.clear()
    return payment_id


def credit_balance(email: str, payments: pd.DataFrame, bookings: pd.DataFrame) -> int:
    """Crediti acquistati meno prenotazioni confermate. Negativo = da pagare."""
    target = norm_email(email)
    bought = 0
    if not payments.empty:
        bought = int(payments.loc[payments["email"] == target, "credits"].sum())
    used = 0
    if not bookings.empty:
        used = int(
            (
                (bookings["email"] == target)
                & (bookings["status"] != "cancelled")
            ).sum()
        )
    return bought - used


def balance_live(email: str) -> int:
    """Saldo letto direttamente dal foglio, senza cache."""
    target = norm_email(email)
    bought = sum(
        int(pd.to_numeric(r.get("credits"), errors="coerce") or 0)
        for r in _sheet("payments").get_all_records()
        if norm_email(r.get("email")) == target
    )
    used = sum(
        1 for r in _sheet("bookings").get_all_records()
        if norm_email(r.get("email")) == target
        and (r.get("status") or "confirmed") != "cancelled"
    )
    return bought - used


def balances_all(payments: pd.DataFrame, bookings: pd.DataFrame) -> pd.DataFrame:
    """Tabella riepilogativa per la pagina Admin."""
    emails = set()
    if not payments.empty:
        emails |= set(payments["email"])
    if not bookings.empty:
        emails |= set(bookings.loc[bookings["status"] != "cancelled", "email"])
    if not emails:
        return pd.DataFrame(columns=["email", "name", "acquistati", "usati", "saldo"])

    rows = []
    for e in sorted(emails):
        bought = int(payments.loc[payments["email"] == e, "credits"].sum()) if not payments.empty else 0
        used = int(((bookings["email"] == e) & (bookings["status"] != "cancelled")).sum()) if not bookings.empty else 0
        name = ""
        if not payments.empty:
            match = payments.loc[payments["email"] == e, "name"]
            if not match.empty:
                name = match.iloc[-1]
        if not name and not bookings.empty:
            match = bookings.loc[bookings["email"] == e, "name"]
            if not match.empty:
                name = match.iloc[-1]
        rows.append({
            "email": e, "name": name,
            "acquistati": bought, "usati": used, "saldo": bought - used,
        })
    return pd.DataFrame(rows).sort_values("saldo")