from datetime import date

import pandas as pd
import streamlit as st

import data

st.set_page_config(page_title="Admin", page_icon="🔒", layout="wide")
st.title("🔒 Bookings")

if "admin_ok" not in st.session_state:
    st.session_state.admin_ok = False

if not st.session_state.admin_ok:
    pw = st.text_input("Password", type="password")
    if st.button("Enter"):
        if pw == st.secrets["admin_password"]:
            st.session_state.admin_ok = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()

if st.button("Refresh"):
    data.load_lessons.clear()
    data.load_bookings.clear()
    st.rerun()

lessons = data.load_lessons()
bookings = data.load_bookings()

if bookings.empty:
    st.info("No bookings yet.")
    st.stop()

merged = bookings.merge(lessons, on="lesson_id", how="left")
merged = merged.sort_values(["date", "time", "timestamp"], na_position="last")

active = merged[merged["status"] != "cancelled"]

c1, c2, c3 = st.columns(3)
c1.metric("Confirmed", len(active))
c2.metric("Cancelled", len(merged) - len(active))
c3.metric(
    "Upcoming",
    len(active[active["date"] >= date.today()]) if not active.empty else 0,
)

st.subheader("By class")
per_class = (
    active.groupby(["lesson_id", "date", "time", "title", "capacity"])
    .size()
    .reset_index(name="booked")
)
per_class["free"] = (per_class["capacity"] - per_class["booked"]).clip(lower=0)
st.dataframe(per_class, use_container_width=True, hide_index=True)

st.subheader("All bookings")
st.dataframe(
    merged[
        ["booking_id", "date", "time", "title", "name", "email", "phone",
         "timestamp", "status"]
    ],
    use_container_width=True,
    hide_index=True,
)

st.download_button(
    "Download CSV",
    merged.to_csv(index=False).encode("utf-8"),
    file_name=f"bookings_{date.today().isoformat()}.csv",
    mime="text/csv",
)

st.subheader("Cancel a booking")
ref = st.text_input("Booking reference")
if st.button("Cancel", type="primary") and ref.strip():
    if data.cancel_booking(ref.strip().upper()):
        st.success(f"{ref.strip().upper()} cancelled.")
        st.rerun()
    else:
        st.error("Reference not found.")