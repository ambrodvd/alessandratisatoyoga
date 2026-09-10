from datetime import date, time, timedelta

import pandas as pd
import streamlit as st

import data
import mailer

st.title("🔒 Gestione")

if "admin_ok" not in st.session_state:
    st.session_state.admin_ok = False

if not st.session_state.admin_ok:
    pw = st.text_input("Password", type="password")
    if st.button("Entra"):
        if pw == st.secrets["admin_password"]:
            st.session_state.admin_ok = True
            st.rerun()
        else:
            st.error("Password errata.")
    st.stop()

if st.button("Aggiorna dati"):
    data.load_lessons.clear()
    data.load_bookings.clear()
    data.load_payments.clear()
    data.load_categories.clear()
    st.rerun()

lessons = data.load_lessons()
bookings = data.load_bookings()
payments = data.load_payments()
categories = data.load_categories()

tab_lezioni, tab_saldi, tab_pren, tab_pag = st.tabs(
    ["Lezioni", "Saldi", "Prenotazioni", "Pagamenti"]
)

# =============================================================
# LEZIONI
# =============================================================
with tab_lezioni:
    sub_cat, sub_les = st.tabs(["Categorie", "Calendario"])

    # ---------- categorie ----------
    with sub_cat:
        st.subheader("Crea una categoria")
        st.caption(
            "Le categorie sono i tipi di lezione ricorrenti. "
            "Definisci una volta nome, modalità, luogo e prezzi; "
            "poi crei le singole lezioni scegliendo la categoria."
        )

        cat_mode = st.radio(
            "Modalità",
            options=["presenza", "online"],
            format_func=lambda m: "📍 In presenza" if m == "presenza" else "💻 Online",
            horizontal=True,
            key="cat_mode_new",
        )

        with st.form("nuova_categoria"):
            cat_name = st.text_input("Nome", placeholder="es. Morning Glory")

            if cat_mode == "online":
                cat_location = st.text_input(
                    "Link Zoom", placeholder="https://zoom.us/j/..."
                )
            else:
                cat_location = st.text_input(
                    "Luogo", placeholder="Via Roma 12, Milano"
                )

            c1, c2, c3 = st.columns(3)
            cat_single = c1.number_input(
                "Prezzo singola €", min_value=0.0, value=15.0, step=1.0
            )
            cat_pack = c2.number_input(
                "Prezzo pacchetto €", min_value=0.0, value=120.0, step=5.0
            )
            cat_credits = c3.number_input(
                "Lezioni nel pacchetto", min_value=1, max_value=100, value=10
            )

            crea_cat = st.form_submit_button("Crea categoria", type="primary")

        if crea_cat:
            if not cat_name.strip():
                st.error("Il nome è obbligatorio.")
            elif cat_mode == "online" and not cat_location.strip().startswith("http"):
                st.error("Per le categorie online serve un link valido.")
            else:
                cid = data.add_category(
                    name=cat_name,
                    mode=cat_mode,
                    location=cat_location,
                    price_single=cat_single,
                    price_package=cat_pack,
                    package_credits=int(cat_credits),
                )
                st.success(f"Categoria {cid} creata.")
                st.rerun()

        st.divider()
        st.subheader("Categorie esistenti")

        if categories.empty:
            st.info("Nessuna categoria. Creane una qui sopra per iniziare.")
        else:
            st.dataframe(categories, use_container_width=True, hide_index=True)

            def _label_cat(cid: str) -> str:
                nome = categories.loc[
                    categories["category_id"] == cid, "name"
                ].iloc[0]
                return f"{cid} · {nome}"

            st.markdown("**Modifica una categoria**")
            cid_sel = st.selectbox(
                "Categoria",
                options=list(categories["category_id"]),
                format_func=_label_cat,
                key="cat_edit_sel",
            )
            row = categories[categories["category_id"] == cid_sel].iloc[0]

            e_mode = st.radio(
                "Modalità",
                options=["presenza", "online"],
                index=0 if row["mode"] != "online" else 1,
                format_func=lambda m: "📍 In presenza" if m == "presenza" else "💻 Online",
                horizontal=True,
                key="cat_mode_edit",
            )

            with st.form("modifica_categoria"):
                e_name = st.text_input("Nome", value=row["name"], key="cat_e_name")
                e_location = st.text_input(
                    "Link Zoom" if e_mode == "online" else "Luogo",
                    value=row["location"],
                    key="cat_e_location",
                )
                d1, d2, d3 = st.columns(3)
                e_single = d1.number_input(
                    "Prezzo singola €",
                    min_value=0.0,
                    value=float(row["price_single"]),
                    step=1.0,
                    key="cat_e_single",
                )
                e_pack = d2.number_input(
                    "Prezzo pacchetto €",
                    min_value=0.0,
                    value=float(row["price_package"]),
                    step=5.0,
                    key="cat_e_pack",
                )
                e_credits = d3.number_input(
                    "Lezioni nel pacchetto",
                    min_value=1,
                    max_value=100,
                    value=int(row["package_credits"]) or 10,
                    key="cat_e_credits",
                )
                salva = st.form_submit_button("Salva modifiche")

            if salva:
                if data.update_category(
                    category_id=cid_sel,
                    name=e_name,
                    mode=e_mode,
                    location=e_location,
                    price_single=e_single,
                    price_package=e_pack,
                    package_credits=int(e_credits),
                ):
                    st.success("Categoria aggiornata.")
                    st.caption(
                        "Le lezioni già create mantengono i dati precedenti: "
                        "la modifica vale per quelle nuove."
                    )
                    st.rerun()
                else:
                    st.error("Categoria non trovata.")

            st.markdown("**Elimina una categoria**")
            cid_del = st.selectbox(
                "Categoria da eliminare",
                options=list(categories["category_id"]),
                format_func=_label_cat,
                key="cat_del_sel",
            )
            ok_del = st.checkbox("Confermo", key="cat_del_ok")
            if st.button("Elimina categoria", key="cat_del_btn") and ok_del:
                if data.delete_category(cid_del):
                    st.success(f"{cid_del} eliminata.")
                    st.rerun()
                else:
                    st.error("Categoria non trovata.")

    # ---------- calendario ----------
    with sub_les:
        st.subheader("Aggiungi lezioni")

        if categories.empty:
            st.warning("Crea prima almeno una categoria nella scheda Categorie.")
        else:
            docenti_noti = (
                sorted(lessons["teacher"].unique()) if not lessons.empty else []
            )

            def _label_cat_new(cid: str) -> str:
                r = categories[categories["category_id"] == cid].iloc[0]
                dove = (
                    "💻 online"
                    if r["mode"] == "online"
                    else "📍 " + (r["location"] or "in presenza")
                )
                return f"{r['name']} · {dove}"

            with st.form("nuova_lezione"):
                l_cat = st.selectbox(
                    "Categoria",
                    options=list(categories["category_id"]),
                    format_func=_label_cat_new,
                    key="les_cat",
                )

                c1, c2 = st.columns(2)
                l_teacher = c1.text_input(
                    "Insegnante",
                    value=docenti_noti[0] if docenti_noti else "",
                    key="les_teacher",
                )
                l_capacity = c2.number_input(
                    "Posti", min_value=1, max_value=100, value=12, key="les_capacity"
                )

                c3, c4 = st.columns(2)
                l_date = c3.date_input(
                    "Data", value=date.today() + timedelta(days=1), key="les_date"
                )
                l_time = c4.time_input(
                    "Ora",
                    value=time(18, 30),
                    step=timedelta(minutes=15),
                    key="les_time",
                )

                st.markdown("**Ripeti** — lascia a 1 per una lezione singola")
                c5, c6 = st.columns(2)
                ripetizioni = c5.number_input(
                    "Numero di settimane",
                    min_value=1,
                    max_value=52,
                    value=1,
                    key="les_ripeti",
                )
                c6.caption("Stessa lezione ogni settimana, stesso giorno e ora.")

                crea = st.form_submit_button("Crea", type="primary")

            if crea:
                cat = categories[categories["category_id"] == l_cat].iloc[0]
                creati, errori = [], []
                for i in range(int(ripetizioni)):
                    giorno = l_date + timedelta(weeks=i)
                    try:
                        lid = data.add_lesson(
                            date_str=giorno.isoformat(),
                            time_str=l_time.strftime("%H:%M"),
                            title=cat["name"],
                            teacher=l_teacher,
                            capacity=int(l_capacity),
                            mode=cat["mode"],
                            location=cat["location"],
                            category_id=l_cat,
                        )
                        creati.append(f"{lid} — {giorno.strftime('%d/%m/%Y')}")
                    except Exception as exc:
                        errori.append(f"{giorno.strftime('%d/%m/%Y')}: {exc}")

                if creati:
                    st.success(f"Create {len(creati)} lezioni.")
                    st.write("\n".join(f"- {c}" for c in creati))
                if errori:
                    st.error("Alcune non sono state create:")
                    st.write("\n".join(f"- {e}" for e in errori))
                data.load_lessons.clear()

        st.divider()
        st.subheader("Calendario")

        if lessons.empty:
            st.info("Nessuna lezione in calendario.")
        else:
            solo_future = st.checkbox(
                "Mostra solo le future", value=True, key="cal_solo_future"
            )
            vista = lessons[lessons["date"] >= date.today()] if solo_future else lessons
            vista = vista.sort_values(["date", "time"])

            if vista.empty:
                st.info("Nessuna lezione futura.")
            else:
                taken = data.seats_taken(bookings)
                vista = vista.assign(
                    prenotati=lambda d: d["lesson_id"].map(taken).fillna(0).astype(int)
                )
                vista = vista.assign(
                    liberi=lambda d: (d["capacity"] - d["prenotati"]).clip(lower=0)
                )
                st.dataframe(
                    vista[
                        [
                            "lesson_id", "date", "time", "title", "teacher",
                            "mode", "location", "capacity", "prenotati", "liberi",
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True,
                )

                st.subheader("Elimina una lezione")
                st.caption(
                    "Le prenotazioni già registrate restano nel foglio ma perdono "
                    "il collegamento: annullale prima."
                )

                def _label_les(lid: str) -> str:
                    r = vista[vista["lesson_id"] == lid].iloc[0]
                    return (
                        f"{lid} · {r['date'].strftime('%d/%m/%Y')} {r['time']} · "
                        f"{r['title']} ({r['prenotati']} prenotati)"
                    )

                da_eliminare = st.selectbox(
                    "Lezione",
                    options=list(vista["lesson_id"]),
                    format_func=_label_les,
                    key="les_del_sel",
                )
                conferma = st.checkbox("Confermo l'eliminazione", key="les_del_ok")
                if st.button("Elimina lezione", key="les_del_btn") and conferma:
                    if data.delete_lesson(da_eliminare):
                        st.success(f"{da_eliminare} eliminata.")
                        st.rerun()
                    else:
                        st.error("Lezione non trovata.")

# =============================================================
# SALDI
# =============================================================
with tab_saldi:
    balances = data.balances_all(payments, bookings, lessons, categories)
    if balances.empty:
        st.info("Nessun dato.")
    else:
        debtors = balances[balances["saldo"] < 0]
        c1, c2 = st.columns(2)
        c1.metric("Posizioni con saldo negativo", len(debtors))
        c2.metric(
            "Lezioni non saldate",
            int(-debtors["saldo"].sum()) if not debtors.empty else 0,
        )

        if not debtors.empty:
            st.error("Da incassare")
            st.dataframe(
                debtors[["email", "name", "categoria", "saldo"]],
                use_container_width=True,
                hide_index=True,
            )

        st.subheader("Tutti i saldi")
        filtro_cat = st.selectbox(
            "Filtra per categoria",
            options=["tutte"] + sorted(balances["categoria"].unique()),
            key="saldi_filtro_cat",
        )
        vista_saldi = (
            balances
            if filtro_cat == "tutte"
            else balances[balances["categoria"] == filtro_cat]
        )
        st.dataframe(
            vista_saldi[["email", "name", "categoria", "acquistati", "usati", "saldo"]],
            use_container_width=True,
            hide_index=True,
        )
        st.download_button(
            "Scarica saldi CSV",
            balances.to_csv(index=False).encode("utf-8"),
            file_name=f"saldi_{date.today().isoformat()}.csv",
            mime="text/csv",
            key="dl_saldi",
        )

# =============================================================
# PRENOTAZIONI
# =============================================================
with tab_pren:
    if bookings.empty:
        st.info("Nessuna prenotazione.")
    else:
        merged = bookings.merge(lessons, on="lesson_id", how="left")
        merged["date"] = pd.to_datetime(merged["date"], errors="coerce")
        merged = merged.sort_values(["date", "time", "timestamp"], na_position="last")
        active = merged[merged["status"] != "cancelled"]
        oggi = pd.Timestamp(date.today())

        c1, c2, c3 = st.columns(3)
        c1.metric("Confermate", len(active))
        c2.metric("Annullate", len(merged) - len(active))
        c3.metric(
            "Future",
            int((active["date"] >= oggi).sum()) if not active.empty else 0,
        )

        colonne = [
            c
            for c in ["booking_id", "date", "time", "title", "name", "email",
                      "phone", "timestamp", "status"]
            if c in merged.columns
        ]
        st.dataframe(merged[colonne], use_container_width=True, hide_index=True)
        st.download_button(
            "Scarica prenotazioni CSV",
            merged.to_csv(index=False).encode("utf-8"),
            file_name=f"prenotazioni_{date.today().isoformat()}.csv",
            mime="text/csv",
            key="dl_pren",
        )

        st.subheader("Annulla una prenotazione")
        ref = st.text_input("Codice prenotazione", key="pren_ref")
        avvisa = st.checkbox(
            "Invia email di annullamento", value=True, key="pren_avvisa"
        )
        if st.button("Annulla", type="primary", key="pren_btn") and ref.strip():
            code = ref.strip().upper()
            row = merged[merged["booking_id"] == code]
            if data.cancel_booking(code):
                st.success(f"{code} annullata.")
                if avvisa and not row.empty:
                    r = row.iloc[0]
                    try:
                        mailer.send_cancellation(
                            to=r["email"],
                            name=r["name"],
                            title=r.get("title", ""),
                            date_str=(
                                r["date"].strftime("%d/%m/%Y")
                                if pd.notna(r.get("date"))
                                else ""
                            ),
                            time_str=r.get("time", ""),
                        )
                    except Exception:
                        st.warning("Annullata, ma l'email non è partita.")
                st.rerun()
            else:
                st.error("Codice non trovato.")

# =============================================================
# PAGAMENTI
# =============================================================
with tab_pag:
    st.subheader("Registra un pagamento")

    if categories.empty:
        st.warning("Crea prima almeno una categoria.")
    else:
        pag_cat = st.selectbox(
            "Categoria acquistata",
            options=list(categories["category_id"]),
            format_func=lambda c: (
                categories.loc[categories["category_id"] == c, "name"].iloc[0]
            ),
            key="pag_cat",
        )
        cat_row = categories[categories["category_id"] == pag_cat].iloc[0]
        st.caption(
            f"Listino: singola € {cat_row['price_single']:.2f} · "
            f"pacchetto € {cat_row['price_package']:.2f} "
            f"per {int(cat_row['package_credits'])} lezioni"
        )

        tipo = st.radio(
            "Tipo",
            options=["pacchetto", "singola", "personalizzato"],
            horizontal=True,
            key="pag_tipo",
        )

        if tipo == "pacchetto":
            pre_credits = int(cat_row["package_credits"]) or 1
            pre_amount = float(cat_row["price_package"])
        elif tipo == "singola":
            pre_credits = 1
            pre_amount = float(cat_row["price_single"])
        else:
            pre_credits, pre_amount = 1, 0.0

        with st.form("nuovo_pagamento"):
            c1, c2 = st.columns(2)
            p_email = c1.text_input("Email", key="pag_email")
            p_name = c2.text_input("Nome", key="pag_name")

            c3, c4, c5 = st.columns(3)
            p_credits = c3.number_input(
                "Lezioni acquistate", min_value=1, value=pre_credits,
                step=1, key="pag_credits",
            )
            p_amount = c4.number_input(
                "Importo €", min_value=0.0, value=pre_amount,
                step=5.0, key="pag_amount",
            )
            p_method = c5.selectbox(
                "Metodo", ["PayPal", "Bonifico", "Contanti", "Altro"],
                key="pag_method",
            )
            p_date = st.date_input(
                "Data pagamento", value=date.today(), key="pag_date"
            )
            p_note = st.text_input("Nota (facoltativa)", key="pag_note")
            ok = st.form_submit_button("Registra", type="primary")

        if ok:
            if "@" not in p_email:
                st.error("Email non valida.")
            else:
                pid = data.add_payment(
                    email=p_email, name=p_name, category_id=pag_cat,
                    credits=int(p_credits), amount_eur=float(p_amount),
                    date_str=p_date.isoformat(), method=p_method, note=p_note,
                )
                saldo = data.balance_live(p_email, pag_cat)
                st.success(
                    f"Pagamento {pid} registrato. "
                    f"Saldo {cat_row['name']}: {saldo} lezioni."
                )

    st.divider()
    if payments.empty:
        st.info("Nessun pagamento registrato.")
    else:
        vista_pag = payments.copy()
        if not categories.empty:
            nomi = dict(zip(categories["category_id"], categories["name"]))
            vista_pag["categoria"] = vista_pag["category_id"].map(nomi).fillna("—")
        st.metric("Incassato totale", f"€ {payments['amount_eur'].sum():,.2f}")
        st.dataframe(vista_pag, use_container_width=True, hide_index=True)