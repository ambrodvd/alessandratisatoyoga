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
    "payment_id", "email", "name", "category_id", "credits",
    "amount_eur", "date", "method", "note",
]

CATEGORY_COLUMNS = [
    "category_id", "name", "mode", "location",
    "price_single", "price_package", "package_credits",
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


# =============================================================
# CATEGORIE
# =============================================================

@st.cache_data(ttl=120, show_spinner=False)
def load_categories() -> pd.DataFrame:
    df = pd.DataFrame(_sheet("categories").get_all_records())
    if df.empty:
        return pd.DataFrame(columns=CATEGORY_COLUMNS)
    df["category_id"] = df["category_id"].astype(str)
    df["mode"] = (
        df["mode"].astype(str).str.strip().str.lower()
        .replace("", "presenza").fillna("presenza")
    )
    df["location"] = df["location"].astype(str).fillna("")
    for col in ("price_single", "price_package"):
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
    df["package_credits"] = (
        pd.to_numeric(df["package_credits"], errors="coerce").fillna(0).astype(int)
    )
    return df


def next_category_id() -> str:
    records = _sheet("categories").get_all_records()
    nums = []
    for r in records:
        val = str(r.get("category_id", "")).strip().upper()
        if val.startswith("C") and val[1:].isdigit():
            nums.append(int(val[1:]))
    return f"C{(max(nums) + 1) if nums else 1:03d}"


def add_category(
    name: str, mode: str, location: str,
    price_single: float, price_package: float, package_credits: int,
) -> str:
    category_id = next_category_id()
    _sheet("categories").append_row(
        [
            category_id, name.strip(), mode.strip().lower(), location.strip(),
            float(price_single), float(price_package), int(package_credits),
        ],
        value_input_option="USER_ENTERED",
    )
    load_categories.clear()
    return category_id


def update_category(
    category_id: str, name: str, mode: str, location: str,
    price_single: float, price_package: float, package_credits: int,
) -> bool:
    ws = _sheet("categories")
    cell = ws.find(str(category_id))
    if cell is None or cell.col != 1:
        return False
    ws.update(
        f"A{cell.row}:G{cell.row}",
        [[
            str(category_id), name.strip(), mode.strip().lower(), location.strip(),
            float(price_single), float(price_package), int(package_credits),
        ]],
        value_input_option="USER_ENTERED",
    )
    load_categories.clear()
    return True


def delete_category(category_id: str) -> bool:
    ws = _sheet("categories")
    cell = ws.find(str(category_id))
    if cell is None or cell.col != 1:
        return False
    ws.delete_rows(cell.row)
    load_categories.clear()
    return True


# =============================================================
# LEZIONI
# =============================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_lessons() -> pd.DataFrame:
    df = pd.DataFrame(_sheet("lessons").get_all_records())
    if df.empty:
        return pd.DataFrame(
            columns=["lesson_id", "date", "time", "title", "teacher",
                     "capacity", "mode", "location", "category_id"]
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
    for col in ("location", "category_id"):
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].astype(str).fillna("")
    return df.dropna(subset=["date"])


def next_lesson_id() -> str:
    records = _sheet("lessons").get_all_records()
    nums = []
    for r in records:
        val = str(r.get("lesson_id", "")).strip().upper()
        if val.startswith("L") and val[1:].isdigit():
            nums.append(int(val[1:]))
    return f"L{(max(nums) + 1) if nums else 1:03d}"


def add_lesson(
    date_str: str, time_str: str, title: str, teacher: str,
    capacity: int, mode: str = "presenza", location: str = "",
    category_id: str = "",
) -> str:
    lesson_id = next_lesson_id()
    _sheet("lessons").append_row(
        [
            lesson_id, date_str, time_str, title.strip(), teacher.strip(),
            int(capacity), mode.strip().lower(), location.strip(), str(category_id),
        ],
        value_input_option="USER_ENTERED",
    )
    load_lessons.clear()
    return lesson_id


def delete_lesson(lesson_id: str) -> bool:
    ws = _sheet("lessons")
    cell = ws.find(str(lesson_id))
    if cell is None or cell.col != 1:
        return False
    ws.delete_rows(cell.row)
    load_lessons.clear()
    return True


# =============================================================
# PRENOTAZIONI
# =============================================================

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


# =============================================================
# PAGAMENTI E SALDI
# =============================================================

@st.cache_data(ttl=60, show_spinner=False)
def load_payments() -> pd.DataFrame:
    df = pd.DataFrame(_sheet("payments").get_all_records())
    if df.empty:
        return pd.DataFrame(columns=PAYMENT_COLUMNS)
    df["email"] = df["email"].map(norm_email)
    if "category_id" not in df.columns:
        df["category_id"] = ""
    df["category_id"] = df["category_id"].astype(str).str.strip()
    df["credits"] = pd.to_numeric(df["credits"], errors="coerce").fillna(0).astype(int)
    df["amount_eur"] = pd.to_numeric(df["amount_eur"], errors="coerce").fillna(0.0)
    return df


def add_payment(
    email: str, name: str, category_id: str, credits: int,
    amount_eur: float, date_str: str, method: str, note: str = "",
) -> str:
    payment_id = "P" + uuid.uuid4().hex[:6].upper()
    _sheet("payments").append_row(
        [
            payment_id, norm_email(email), name.strip(), str(category_id).strip(),
            int(credits), float(amount_eur), date_str, method.strip(), note.strip(),
        ],
        value_input_option="USER_ENTERED",
    )
    load_payments.clear()
    return payment_id


def _cat_by_lesson(lessons: pd.DataFrame) -> dict:
    if lessons.empty:
        return {}
    return {
        str(lid): str(cid).strip()
        for lid, cid in zip(lessons["lesson_id"], lessons["category_id"])
    }


def balance_live(email: str, category_id: str) -> int:
    """Saldo di categoria letto direttamente dal foglio, senza cache."""
    target = norm_email(email)
    cat = str(category_id).strip()

    bought = sum(
        int(pd.to_numeric(r.get("credits"), errors="coerce") or 0)
        for r in _sheet("payments").get_all_records()
        if norm_email(r.get("email")) == target
        and str(r.get("category_id", "")).strip() == cat
    )

    mappa = {
        str(r.get("lesson_id")): str(r.get("category_id", "")).strip()
        for r in _sheet("lessons").get_all_records()
    }
    used = sum(
        1
        for r in _sheet("bookings").get_all_records()
        if norm_email(r.get("email")) == target
        and (r.get("status") or "confirmed") != "cancelled"
        and mappa.get(str(r.get("lesson_id")), "") == cat
    )

    return bought - used


def balances_all(
    payments: pd.DataFrame, bookings: pd.DataFrame,
    lessons: pd.DataFrame, categories: pd.DataFrame,
) -> pd.DataFrame:
    """Riepilogo per coppia (email, categoria)."""
    colonne = ["email", "name", "categoria", "category_id",
               "acquistati", "usati", "saldo"]

    mappa = _cat_by_lesson(lessons)
    nome_cat = (
        dict(zip(categories["category_id"], categories["name"]))
        if not categories.empty else {}
    )

    attive = (
        bookings[bookings["status"] != "cancelled"]
        if not bookings.empty else bookings
    )

    coppie = set()
    if not payments.empty:
        coppie |= set(zip(payments["email"], payments["category_id"]))
    if not attive.empty:
        for _, b in attive.iterrows():
            coppie.add((b["email"], mappa.get(str(b["lesson_id"]), "")))

    if not coppie:
        return pd.DataFrame(columns=colonne)

    nomi = {}
    for df in (payments, bookings):
        if not df.empty:
            for _, r in df.iterrows():
                if r.get("name"):
                    nomi[r["email"]] = r["name"]

    righe = []
    for mail, cat in sorted(coppie):
        bought = 0
        if not payments.empty:
            bought = int(
                payments.loc[
                    (payments["email"] == mail) & (payments["category_id"] == cat),
                    "credits",
                ].sum()
            )
        used = 0
        if not attive.empty:
            used = sum(
                1
                for _, b in attive.iterrows()
                if b["email"] == mail and mappa.get(str(b["lesson_id"]), "") == cat
            )
        righe.append({
            "email": mail,
            "name": nomi.get(mail, ""),
            "categoria": nome_cat.get(cat, "— senza categoria —" if not cat else cat),
            "category_id": cat,
            "acquistati": bought,
            "usati": used,
            "saldo": bought - used,
        })

    return pd.DataFrame(righe, columns=colonne).sort_values(["saldo", "email"])