from datetime import date

import streamlit as st

import data

st.set_page_config(page_title="Book a class", page_icon="🧘", layout="centered")

st.title("🧘 Book a class")

try:
    lessons = data.load_lessons()
    bookings = data.load_bookings()
except Exception as exc:
    st.error("Could not reach the schedule. Please try again in a moment.")
    st.exception(exc)  # remove this line once it works
    st.stop()

if lessons.empty:
    st.info("No classes scheduled yet.")
    st.stop()

upcoming = lessons[lessons["date"] >= date.today()].sort_values(["date", "time"])
if upcoming.empty:
    st.info("No upcoming classes.")
    st.stop()

taken = data.seats_taken(bookings)
upcoming = upcoming.assign(
    booked=lambda d: d["lesson_id"].map(taken).fillna(0).astype(int)
)
upcoming = upcoming.assign(
    free=lambda d: (d["capacity"] - d["booked"]).clip(lower=0)
)

chosen_date = st.selectbox(
    "Date",
    options=sorted(upcoming["date"].unique()),
    format_func=lambda d: d.strftime("%A %d %B %Y"),
)

day = upcoming[upcoming["date"] == chosen_date]
slots = list(day.itertuples(index=False))


def slot_label(row) -> str:
    tail = f"{row.free} spots left" if row.free > 0 else "FULL"
    return f"{row.time} · {row.title} · {row.teacher} — {tail}"


choice = st.radio("Class", options=slots, format_func=slot_label)

st.divider()

if choice.free <= 0:
    st.error("This class is full. Pick another one.")
    st.stop()

with st.form("booking_form", clear_on_submit=False):
    name = st.text_input("Full name")
    email = st.text_input("Email")
    phone = st.text_input("Phone (optional)")
    consent = st.checkbox(
        "I agree to my details being stored for the purpose of managing this booking."
    )
    submitted = st.form_submit_button("Confirm booking", type="primary")

if submitted:
    if not name.strip():
        st.error("Please enter your name.")
    elif "@" not in email or "." not in email.split("@")[-1]:
        st.error("Please enter a valid email address.")
    elif not consent:
        st.error("Please accept the data notice to continue.")
    else:
        with st.spinner("Confirming..."):
            if data.already_booked(choice.lesson_id, email):
                st.warning("You're already booked for this class.")
            elif data.count_live(choice.lesson_id) >= choice.capacity:
                st.error("Someone just took the last spot. Please choose another class.")
                data.load_bookings.clear()
            else:
                ref = data.add_booking(choice.lesson_id, name, email, phone)
                st.success(
                    f"Booked — {choice.title} on "
                    f"{chosen_date.strftime('%d %B')} at {choice.time}.\n\n"
                    f"Your reference: **{ref}**"
                )
                st.balloons()