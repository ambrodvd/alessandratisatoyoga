"""Data access layer. Google Sheets today, swappable for Postgres later."""

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
    "booking_id",
    "lesson_id",
    "name",
    "email",
    "phone",
    "timestamp",
    "status",
]


@st.cache_resource(show_spinner=False)
def _client() -> gspread.Client:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=SCOPES
    )
    return gspread.authorize(creds)


def _sheet(tab: str) -> gspread.Worksheet:
    return _client().open_by_key(st.secrets["spreadsheet_id"]).worksheet(tab)


@st.cache_data(ttl=300, show_spinner=False)
def load_lessons() -> pd.DataFrame:
    df = pd.DataFrame(_sheet("lessons").get_all_records())
    if df.empty:
        return pd.DataFrame(
            columns=["lesson_id", "date", "time", "title", "teacher", "capacity"]
        )
    df["lesson_id"] = df["lesson_id"].astype(str)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["time"] = df["time"].astype(str)
    df["capacity"] = (
        pd.to_numeric(df["capacity"], errors="coerce").fillna(0).astype(int)
    )
    return df.dropna(subset=["date"])


@st.cache_data(ttl=20, show_spinner=False)
def load_bookings() -> pd.DataFrame:
    df = pd.DataFrame(_sheet("bookings").get_all_records())
    if df.empty:
        return pd.DataFrame(columns=BOOKING_COLUMNS)
    df["lesson_id"] = df["lesson_id"].astype(str)
    if "status" not in df.columns:
        df["status"] = "confirmed"
    df["status"] = df["status"].replace("", "confirmed").fillna("confirmed")
    return df


def seats_taken(bookings: pd.DataFrame) -> pd.Series:
    """lesson_id -> number of confirmed bookings."""
    if bookings.empty:
        return pd.Series(dtype=int)
    active = bookings[bookings["status"] != "cancelled"]
    if active.empty:
        return pd.Series(dtype=int)
    return active.groupby("lesson_id").size()


def count_live(lesson_id: str) -> int:
    """Uncached read straight from the sheet, for the final capacity check."""
    records = _sheet("bookings").get_all_records()
    return sum(
        1
        for r in records
        if str(r.get("lesson_id")) == str(lesson_id)
        and (r.get("status") or "confirmed") != "cancelled"
    )


def already_booked(lesson_id: str, email: str) -> bool:
    records = _sheet("bookings").get_all_records()
    email = email.strip().lower()
    return any(
        str(r.get("lesson_id")) == str(lesson_id)
        and str(r.get("email", "")).strip().lower() == email
        and (r.get("status") or "confirmed") != "cancelled"
        for r in records
    )


def add_booking(lesson_id: str, name: str, email: str, phone: str) -> str:
    booking_id = uuid.uuid4().hex[:8].upper()
    _sheet("bookings").append_row(
        [
            booking_id,
            str(lesson_id),
            name.strip(),
            email.strip().lower(),
            phone.strip(),
            datetime.now().isoformat(timespec="seconds"),
            "confirmed",
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
    status_col = BOOKING_COLUMNS.index("status") + 1
    ws.update_cell(cell.row, status_col, "cancelled")
    load_bookings.clear()
    return True