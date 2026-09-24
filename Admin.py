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
    data.load_recordings.clear()
    data.load_recording_shares.clear()
    data.load_recording_packages.clear()
    data.load_package_requests.clear()
    st.rerun()

lessons = data.load_lessons()
bookings = data.load_bookings()
payments = data.load_payments()
categories = data.load_categories()

PAYPAL = st.secrets.get("paypal_me", "")

tab_lezioni, tab_pren, tab_persone, tab_rec, tab_pack = st.tabs(
    ["Lezioni", "Prenotazioni", "Persone e pagamenti", "Lezioni registrate",
     "Pacchetti registrazioni"]
)

# =============================================================
# LEZIONI
# =============================================================
with tab_lezioni:
    sub_les, sub_cat = st.tabs(["Calendario", "Categorie"])

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
                cat_location = st.text_input("Luogo", placeholder="Via Roma 12, Milano")

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
                    name=cat_name, mode=cat_mode, location=cat_location,
                    price_single=cat_single, price_package=cat_pack,
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
                nome = categories.loc[categories["category_id"] == cid, "name"].iloc[0]
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
                    value=row["location"], key="cat_e_location",
                )
                d1, d2, d3 = st.columns(3)
                e_single = d1.number_input(
                    "Prezzo singola €", min_value=0.0,
                    value=float(row["price_single"]), step=1.0, key="cat_e_single",
                )
                e_pack = d2.number_input(
                    "Prezzo pacchetto €", min_value=0.0,
                    value=float(row["price_package"]), step=5.0, key="cat_e_pack",
                )
                e_credits = d3.number_input(
                    "Lezioni nel pacchetto", min_value=1, max_value=100,
                    value=int(row["package_credits"]) or 10, key="cat_e_credits",
                )
                salva = st.form_submit_button("Salva modifiche")

            if salva:
                if data.update_category(
                    category_id=cid_sel, name=e_name, mode=e_mode,
                    location=e_location, price_single=e_single,
                    price_package=e_pack, package_credits=int(e_credits),
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
                format_func=_label_cat, key="cat_del_sel",
            )
            ok_del = st.checkbox(
                "Seleziona la casella se sei sicura di voler cancellare",
                key="cat_del_ok",
            )
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
                    "💻 online" if r["mode"] == "online"
                    else "📍 " + (r["location"] or "in presenza")
                )
                return f"{r['name']} · {dove}"

            with st.form("nuova_lezione"):
                l_cat = st.selectbox(
                    "Categoria", options=list(categories["category_id"]),
                    format_func=_label_cat_new, key="les_cat",
                )
                c1, c2 = st.columns(2)
                l_teacher = c1.text_input(
                    "Insegnante", value=docenti_noti[0] if docenti_noti else "",
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
                    "Ora", value=time(18, 30), step=timedelta(minutes=15),
                    key="les_time",
                )
                st.markdown("**Ripeti** — lascia a 1 per una lezione singola")
                c5, c6 = st.columns(2)
                ripetizioni = c5.number_input(
                    "Numero di settimane", min_value=1, max_value=52, value=1,
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
                            title=cat["name"], teacher=l_teacher,
                            capacity=int(l_capacity), mode=cat["mode"],
                            location=cat["location"], category_id=l_cat,
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
                    vista[["lesson_id", "date", "time", "title", "teacher", "mode",
                           "location", "capacity", "prenotati", "liberi"]],
                    use_container_width=True, hide_index=True,
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
                    "Lezione", options=list(vista["lesson_id"]),
                    format_func=_label_les, key="les_del_sel",
                )
                conferma = st.checkbox(
                    "Seleziona la casella se sei sicura di voler cancellare",
                    key="les_del_ok",
                )
                if st.button("Elimina lezione", key="les_del_btn") and conferma:
                    if data.delete_lesson(da_eliminare):
                        st.success(f"{da_eliminare} eliminata.")
                        st.rerun()
                    else:
                        st.error("Lezione non trovata.")

# =============================================================
# PRENOTAZIONI
# =============================================================
with tab_pren:
    if bookings.empty:
        st.info("Nessuna prenotazione.")
        merged = pd.DataFrame()
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
            "Future", int((active["date"] >= oggi).sum()) if not active.empty else 0
        )

        st.subheader("Filtra")
        f1, f2, f3 = st.columns(3)
        periodo = f1.selectbox(
            "Periodo",
            options=["questa_settimana", "prossima_settimana", "oggi", "giorno",
                     "future", "tutte"],
            format_func=lambda p: {
                "questa_settimana": "Questa settimana",
                "prossima_settimana": "Prossima settimana",
                "oggi": "Oggi",
                "giorno": "Un giorno preciso",
                "future": "Tutte le future",
                "tutte": "Tutte, anche passate",
            }[p],
            key="pren_periodo",
        )

        cat_options = ["tutte"]
        if not categories.empty:
            cat_options += list(categories["category_id"])

        filtro_cat = f2.selectbox(
            "Categoria",
            options=cat_options,
            format_func=lambda c: (
                "Tutte le categorie"
                if c == "tutte"
                else categories.loc[categories["category_id"] == c, "name"].iloc[0]
            ),
            key="pren_categoria",
        )

        solo_attive = f3.checkbox(
            "Solo confermate", value=True, key="pren_solo_attive"
        )

        giorno_sel = None
        if periodo == "giorno":
            giorno_sel = st.date_input("Giorno", value=date.today(), key="pren_giorno")

        d_oggi = date.today()
        dom = pd.Timestamp(d_oggi + timedelta(days=6 - d_oggi.weekday()))

        vp = active if solo_attive else merged
        if periodo == "future":
            vp = vp[vp["date"] >= oggi]
        elif periodo == "oggi":
            vp = vp[vp["date"] == oggi]
        elif periodo == "questa_settimana":
            vp = vp[(vp["date"] >= oggi) & (vp["date"] <= dom)]
        elif periodo == "prossima_settimana":
            vp = vp[(vp["date"] > dom) & (vp["date"] <= dom + pd.Timedelta(days=7))]
        elif periodo == "giorno":
            vp = vp[vp["date"] == pd.Timestamp(giorno_sel)]

        if filtro_cat != "tutte" and "category_id" in vp.columns:
            vp = vp[vp["category_id"].astype(str) == filtro_cat]

        st.caption(f"{len(vp)} prenotazioni")

        if vp.empty:
            st.info("Nessuna prenotazione con questi filtri.")
        else:
            st.markdown("**Per lezione**")
            per_lezione = (
                vp.groupby(["date", "time", "title"], dropna=False)
                .size()
                .reset_index(name="prenotati")
                .sort_values(["date", "time"])
            )
            st.dataframe(per_lezione, use_container_width=True, hide_index=True)

            st.markdown("**Dettaglio**")
            colonne = [
                c for c in ["date", "time", "title", "name", "email",
                            "booking_id", "timestamp", "status"]
                if c in vp.columns
            ]
            st.dataframe(vp[colonne], use_container_width=True, hide_index=True)
            st.download_button(
                "Scarica CSV",
                vp.to_csv(index=False).encode("utf-8"),
                file_name=f"prenotazioni_{date.today().isoformat()}.csv",
                mime="text/csv", key="dl_pren",
            )

    # ---------- aggiungi presenza ----------
    st.divider()
    with st.expander("➕  Aggiungi una presenza"):
        st.caption(
            "Per chi si è presentato senza prenotare. "
            "La lezione viene scalata dal suo saldo."
        )

        recenti = (
            lessons[lessons["date"] >= date.today() - timedelta(days=30)]
            if not lessons.empty else lessons
        )
        if not recenti.empty:
            recenti = recenti.sort_values("date", ascending=False)

        if recenti.empty:
            st.info("Nessuna lezione disponibile.")
        else:
            noti = pd.DataFrame(columns=["email", "name"])
            if not bookings.empty:
                noti = (
                    bookings.groupby("email", as_index=False)
                    .agg(name=("name", "last"))
                    .sort_values("name")
                )

            opz_noti = ["— nuova persona —"] + list(noti["email"])
            sel_pres = st.selectbox(
                "Persona",
                options=opz_noti,
                format_func=lambda e: (
                    e if e == "— nuova persona —"
                    else f"{noti.loc[noti['email'] == e, 'name'].iloc[0]} ({e})"
                ),
                key="pres_persona",
            )

            if sel_pres != "— nuova persona —":
                pres_email_pre = sel_pres
                pres_name_pre = noti.loc[noti["email"] == sel_pres, "name"].iloc[0]
            else:
                pres_email_pre, pres_name_pre = "", ""

            sfx = sel_pres.replace("@", "_").replace(".", "_")

            def _label_pres(lid: str) -> str:
                r = recenti[recenti["lesson_id"] == lid].iloc[0]
                return f"{r['title']} · {r['date'].strftime('%d/%m/%Y')} ore {r['time']}"

            with st.form("nuova_presenza"):
                lid_pres = st.selectbox(
                    "Lezione",
                    options=list(recenti["lesson_id"]),
                    format_func=_label_pres,
                    key="pres_lezione",
                )
                pc1, pc2 = st.columns(2)
                pres_name = pc1.text_input(
                    "Nome e cognome", value=pres_name_pre, key=f"pres_name_{sfx}"
                )
                pres_email = pc2.text_input(
                    "Email", value=pres_email_pre, key=f"pres_email_{sfx}"
                )
                ok_pres = st.form_submit_button("Aggiungi presenza", type="primary")

            if ok_pres:
                if "@" not in pres_email:
                    st.error("Email non valida.")
                elif not pres_name.strip():
                    st.error("Inserisci il nome.")
                elif data.already_booked(lid_pres, pres_email):
                    st.warning("Questa persona risulta già iscritta a questa lezione.")
                else:
                    lez = recenti[recenti["lesson_id"] == lid_pres].iloc[0]
                    bid = data.add_manual_booking(lid_pres, pres_name, pres_email)
                    saldo = data.balance_live(pres_email, str(lez["category_id"]))
                    st.success(
                        f"Presenza {bid} registrata per {pres_name}. "
                        f"Saldo {lez['title']}: {saldo}."
                    )
                    st.rerun()

    # ---------- presenza fuori calendario ----------
    with st.expander("➕  Presenza fuori calendario"):
        st.caption(
            "Per una lezione che non è nel gestionale: la creo io e ci aggancio "
            "la presenza, così il saldo si scala."
        )

        if categories.empty:
            st.warning("Crea prima almeno una categoria.")
        else:
            noti_fc = pd.DataFrame(columns=["email", "name"])
            if not bookings.empty:
                noti_fc = (
                    bookings.groupby("email", as_index=False)
                    .agg(name=("name", "last"))
                    .sort_values("name")
                )

            opz_fc = ["— nuova persona —"] + list(noti_fc["email"])
            sel_fc = st.selectbox(
                "Persona",
                options=opz_fc,
                format_func=lambda e: (
                    e if e == "— nuova persona —"
                    else f"{noti_fc.loc[noti_fc['email'] == e, 'name'].iloc[0]} ({e})"
                ),
                key="fc_persona",
            )

            if sel_fc != "— nuova persona —":
                fc_email_pre = sel_fc
                fc_name_pre = noti_fc.loc[noti_fc["email"] == sel_fc, "name"].iloc[0]
            else:
                fc_email_pre, fc_name_pre = "", ""

            sfx_fc = sel_fc.replace("@", "_").replace(".", "_")

            con_data = st.checkbox("Conosco la data", value=True, key="fc_con_data")

            with st.form("presenza_fuori_calendario"):
                fc_cat = st.selectbox(
                    "Categoria",
                    options=list(categories["category_id"]),
                    format_func=lambda c: (
                        categories.loc[categories["category_id"] == c, "name"].iloc[0]
                    ),
                    key="fc_cat",
                )

                if con_data:
                    fd1, fd2 = st.columns(2)
                    fc_date = fd1.date_input("Data", value=date.today(), key="fc_date")
                    fc_time = fd2.time_input(
                        "Ora", value=time(18, 30), step=timedelta(minutes=15),
                        key="fc_time",
                    )
                else:
                    fc_date, fc_time = None, None
                    st.caption("Senza data userò la data di oggi come riferimento.")

                fc1, fc2 = st.columns(2)
                fc_name = fc1.text_input(
                    "Nome e cognome", value=fc_name_pre, key=f"fc_name_{sfx_fc}"
                )
                fc_email = fc2.text_input(
                    "Email", value=fc_email_pre, key=f"fc_email_{sfx_fc}"
                )
                fc_note = st.text_input(
                    "Nota (facoltativa)",
                    placeholder="es. lezione privata, sostituzione",
                    key="fc_note",
                )
                ok_fc = st.form_submit_button("Registra presenza", type="primary")

            if ok_fc:
                if "@" not in fc_email:
                    st.error("Email non valida.")
                elif not fc_name.strip():
                    st.error("Inserisci il nome.")
                else:
                    cat_fc = categories[categories["category_id"] == fc_cat].iloc[0]
                    giorno_fc = fc_date if con_data else date.today()
                    ora_fc = fc_time.strftime("%H:%M") if con_data else ""
                    titolo = cat_fc["name"]
                    if fc_note.strip():
                        titolo = f"{titolo} ({fc_note.strip()})"

                    try:
                        lid_fc = data.add_lesson(
                            date_str=giorno_fc.isoformat(),
                            time_str=ora_fc,
                            title=titolo,
                            teacher="",
                            capacity=1,
                            mode=cat_fc["mode"],
                            location=cat_fc["location"],
                            category_id=fc_cat,
                        )
                        bid_fc = data.add_manual_booking(lid_fc, fc_name, fc_email)
                        saldo = data.balance_live(fc_email, fc_cat)
                        st.success(
                            f"Presenza {bid_fc} registrata per {fc_name} "
                            f"({lid_fc}). Saldo {cat_fc['name']}: {saldo}."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Non sono riuscito a registrare: {exc}")

    # ---------- annulla ----------
    st.divider()
    st.subheader("Annulla una prenotazione")

    annullabili = (
        merged[merged["status"] != "cancelled"].copy()
        if not merged.empty else pd.DataFrame()
    )
    if not annullabili.empty:
        annullabili = annullabili.sort_values("date", na_position="last")

    if annullabili.empty:
        st.info("Nessuna prenotazione attiva.")
    else:
        def _label_annulla(bid: str) -> str:
            r = annullabili[annullabili["booking_id"] == bid].iloc[0]
            giorno = (
                r["date"].strftime("%d/%m/%Y")
                if pd.notna(r.get("date")) else "data ignota"
            )
            return (
                f"{r['name']} — {r.get('title', '?')} — "
                f"{giorno} ore {r.get('time', '')}"
            )

        bid_annulla = st.selectbox(
            "Prenotazione",
            options=list(annullabili["booking_id"]),
            format_func=_label_annulla,
            key="pren_sel_annulla",
        )
        avvisa = st.checkbox(
            "Invia email di annullamento", value=True, key="pren_avvisa"
        )
        conferma_ann = st.checkbox(
            "Seleziona la casella se sei sicura di voler cancellare",
            key="pren_conferma",
        )

        if st.button("Annulla", type="primary", key="pren_btn") and conferma_ann:
            r = annullabili[annullabili["booking_id"] == bid_annulla].iloc[0]
            if data.cancel_booking(bid_annulla):
                st.success(f"Prenotazione di {r['name']} annullata.")
                if avvisa:
                    try:
                        mailer.send_cancellation(
                            to=r["email"],
                            name=r["name"],
                            title=r.get("title", ""),
                            date_str=(
                                r["date"].strftime("%d/%m/%Y")
                                if pd.notna(r.get("date")) else ""
                            ),
                            time_str=r.get("time", ""),
                        )
                    except Exception:
                        st.warning("Annullata, ma l'email non è partita.")
                st.rerun()
            else:
                st.error("Prenotazione non trovata.")

# =============================================================
# PERSONE E PAGAMENTI
# =============================================================
with tab_persone:
    balances = data.balances_all(payments, bookings, lessons, categories)

    # ---------- da incassare ----------
    st.subheader("Da incassare")
    if balances.empty:
        st.info("Nessun dato.")
        debtors = pd.DataFrame()
    else:
        debtors = balances[balances["saldo"] < 0]
        c1, c2 = st.columns(2)
        c1.metric("Da saldare", len(debtors))
        c2.metric(
            "Lezioni non saldate",
            int(-debtors["saldo"].sum()) if not debtors.empty else 0,
        )
        if debtors.empty:
            st.success("Tutti i saldi sono in pari.")
        else:
            dv = debtors.copy()
            dv["da_saldare"] = -dv["saldo"]
            st.dataframe(
                dv[["name", "categoria", "usati", "da_saldare", "email"]].rename(
                    columns={
                        "name": "persona",
                        "usati": "lezioni usate",
                        "da_saldare": "da saldare",
                    }
                ),
                use_container_width=True, hide_index=True,
            )

    # ---------- tutti i saldi ----------
    st.divider()
    st.subheader("Tutti i saldi")

    if balances.empty:
        st.info("Nessun dato.")
    else:
        st.dataframe(
            balances[["name", "categoria", "acquistati", "usati", "extra",
                      "saldo", "email"]]
            .rename(columns={
                "name": "persona",
                "usati": "lezioni usate",
                "extra": "registrazioni",
            }),
            use_container_width=True, hide_index=True,
        )

    # ---------- registra pagamento ----------
    st.divider()
    st.subheader("Registra un pagamento")

    if balances.empty:
        coppie = []
    else:
        coppie = list(
            balances[["email", "name", "categoria", "category_id", "saldo"]]
            .itertuples(index=False)
        )

    opzioni = ["— nuovo utente —"] + [f"{c.email}||{c.category_id}" for c in coppie]
    mappa_coppie = {f"{c.email}||{c.category_id}": c for c in coppie}

    def _label_coppia(key: str) -> str:
        if key == "— nuovo utente —":
            return key
        c = mappa_coppie[key]
        return f"{c.name or c.email} — {c.categoria}  ·  saldo {c.saldo}"

    sel_key = st.selectbox(
        "Persona e categoria",
        options=opzioni,
        format_func=_label_coppia,
        key="sel_utente",
        help="Seleziona per precompilare persona, categoria e importo.",
    )

    if sel_key != "— nuovo utente —":
        scelta = mappa_coppie[sel_key]
        pre_email = scelta.email
        pre_name = scelta.name
        pre_cat = scelta.category_id
        pre_saldo = int(scelta.saldo)
    else:
        pre_email, pre_name, pre_cat, pre_saldo = "", "", "", 0

    suffix = sel_key.replace("@", "_").replace(".", "_").replace("|", "_")

    if categories.empty:
        st.warning("Crea prima almeno una categoria.")
    else:
        tipo = st.radio(
            "Tipo",
            options=["pacchetto", "singola", "personalizzato", "prova"],
            format_func=lambda t: {
                "pacchetto": "Pacchetto",
                "singola": "Lezione singola",
                "personalizzato": "Personalizzato",
                "prova": "🎁 Lezione prova gratuita",
            }[t],
            horizontal=True,
            key="pag_tipo",
        )

        # ---- lezione prova ----
        if tipo == "prova":
            if not pre_email:
                st.warning("Seleziona prima la persona qui sopra.")
            else:
                mie = data.bookings_of(pre_email, bookings, lessons)
                mie = (
                    mie[mie["category_id"].astype(str) != ""]
                    if not mie.empty else mie
                )

                if mie.empty:
                    st.warning("Questa persona non ha prenotazioni registrate.")
                else:
                    def _label_prova(bid: str) -> str:
                        r = mie[mie["booking_id"] == bid].iloc[0]
                        giorno = (
                            r["date"].strftime("%d/%m/%Y")
                            if pd.notna(r.get("date")) else "?"
                        )
                        return f"{r['title']} · {giorno} · {r.get('time', '')}"

                    bid_sel = st.selectbox(
                        "Lezione da regalare",
                        options=list(mie["booking_id"]),
                        format_func=_label_prova,
                        key=f"prova_bid_{suffix}",
                    )
                    r = mie[mie["booking_id"] == bid_sel].iloc[0]
                    cat_prova = categories[
                        categories["category_id"] == str(r["category_id"])
                    ]

                    if cat_prova.empty:
                        st.error("La categoria di questa lezione non esiste più.")
                    else:
                        cp = cat_prova.iloc[0]
                        giorno_txt = (
                            r["date"].strftime("%d/%m/%Y")
                            if pd.notna(r.get("date")) else "?"
                        )
                        st.info(
                            f"Regali **{cp['name']}** del {giorno_txt} "
                            f"alle {r.get('time', '')} — 1 credito gratuito."
                        )
                        avvisa_prova = st.checkbox(
                            "Invia mail di benvenuto", value=True, key="prova_avvisa"
                        )
                        if st.button(
                            "Registra lezione prova", type="primary", key="prova_btn"
                        ):
                            pid = data.add_payment(
                                email=pre_email, name=pre_name,
                                category_id=str(r["category_id"]),
                                credits=1, amount_eur=0.0,
                                date_str=date.today().isoformat(),
                                method="Omaggio", note="lezione prova",
                            )
                            saldo = data.balance_live(
                                pre_email, str(r["category_id"])
                            )
                            st.success(
                                f"Lezione prova {pid} registrata. "
                                f"Saldo {cp['name']}: {saldo}."
                            )
                            if avvisa_prova:
                                try:
                                    mailer.send_trial_gift(
                                        to=pre_email,
                                        name=pre_name or pre_email,
                                        categoria=cp["name"],
                                        date_str=giorno_txt,
                                        time_str=str(r.get("time", "")),
                                        price_single=float(cp["price_single"]),
                                        price_package=float(cp["price_package"]),
                                        package_credits=int(cp["package_credits"]),
                                        pay_base=PAYPAL,
                                    )
                                    st.caption("Mail di benvenuto inviata.")
                                except Exception as exc:
                                    st.warning(
                                        f"Registrata, ma la mail non è partita: {exc}"
                                    )

        # ---- pagamento normale ----
        else:
            lista_cat = list(categories["category_id"])
            idx_cat = lista_cat.index(pre_cat) if pre_cat in lista_cat else 0
            pag_cat = st.selectbox(
                "Categoria acquistata",
                options=lista_cat,
                index=idx_cat,
                format_func=lambda c: (
                    categories.loc[categories["category_id"] == c, "name"].iloc[0]
                ),
                key=f"pag_cat_{suffix}",
            )
            cat_row = categories[categories["category_id"] == pag_cat].iloc[0]
            st.caption(
                f"Listino: singola € {cat_row['price_single']:.2f} · "
                f"pacchetto € {cat_row['price_package']:.2f} "
                f"per {int(cat_row['package_credits'])} lezioni"
            )

            if tipo == "pacchetto":
                pre_credits = int(cat_row["package_credits"]) or 1
                pre_amount = float(cat_row["price_package"])
            elif tipo == "singola":
                pre_credits = abs(pre_saldo) if pre_saldo < 0 else 1
                pre_amount = float(cat_row["price_single"]) * pre_credits
            else:
                pre_credits, pre_amount = 1, 0.0

            if PAYPAL and pre_amount:
                st.markdown(f"**Link da inviare:** `{PAYPAL}/{pre_amount:.2f}EUR`")

            with st.form("nuovo_pagamento"):
                c1, c2 = st.columns(2)
                p_email = c1.text_input(
                    "Email", value=pre_email, key=f"pag_email_{suffix}"
                )
                p_name = c2.text_input(
                    "Nome", value=pre_name, key=f"pag_name_{suffix}"
                )
                c3, c4, c5 = st.columns(3)
                p_credits = c3.number_input(
                    "Lezioni acquistate", min_value=1, value=pre_credits,
                    step=1, key=f"pag_credits_{suffix}_{tipo}",
                )
                p_amount = c4.number_input(
                    "Importo €", min_value=0.0, value=pre_amount,
                    step=5.0, key=f"pag_amount_{suffix}_{tipo}",
                )
                p_method = c5.selectbox(
                    "Metodo",
                    ["PayPal", "Bonifico", "Contanti", "Satispay", "Altro"],
                    key="pag_method",
                )
                p_date = st.date_input(
                    "Data pagamento", value=date.today(), key="pag_date"
                )
                p_note = st.text_input("Nota (facoltativa)", key="pag_note")
                avvisa_pag = st.checkbox(
                    "Invia mail di conferma", value=True, key="pag_avvisa"
                )
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
                    if avvisa_pag:
                        try:
                            mailer.send_payment_receipt(
                                to=p_email, name=p_name.strip() or p_email,
                                categoria=cat_row["name"], credits=int(p_credits),
                                amount_eur=float(p_amount), saldo=saldo,
                                method=p_method,
                            )
                            st.caption("Mail di conferma inviata.")
                        except Exception as exc:
                            st.warning(
                                f"Pagamento salvato, ma la mail non è partita: {exc}"
                            )

    st.divider()
    st.subheader("Storico pagamenti")
    if payments.empty:
        st.info("Nessun pagamento registrato.")
    else:
        vista_pag = payments.copy()
        if not categories.empty:
            nomi = dict(zip(categories["category_id"], categories["name"]))
            vista_pag["categoria"] = vista_pag["category_id"].map(nomi).fillna("—")
        st.metric("Incassato totale", f"€ {payments['amount_eur'].sum():,.2f}")
        st.dataframe(vista_pag, use_container_width=True, hide_index=True)
        if not balances.empty:
            st.download_button(
                "Scarica saldi CSV",
                balances.to_csv(index=False).encode("utf-8"),
                file_name=f"saldi_{date.today().isoformat()}.csv",
                mime="text/csv", key="dl_saldi",
            )

# =============================================================
# LEZIONI REGISTRATE
# =============================================================
with tab_rec:
    nomi_cat = (
        dict(zip(categories["category_id"].astype(str), categories["name"]))
        if not categories.empty else {}
    )

    def _invia_registrazione(destinatari, categoria, giorno, link, altri=False):
        barra = st.progress(0.0)
        inviate, fallite = [], []
        for i, (email, nome) in enumerate(destinatari, 1):
            try:
                if altri:
                    mailer.send_recording_share(
                        to=email, name=nome or email, categoria=categoria,
                        date_str=giorno, link=link,
                    )
                else:
                    mailer.send_recording(
                        to=email, categoria=categoria, date_str=giorno, link=link,
                    )
                inviate.append((email, nome))
            except Exception as exc:
                fallite.append(f"{nome} ({email}): {exc}")
            barra.progress(i / len(destinatari))
        if inviate:
            st.success(f"Inviate {len(inviate)} mail.")
        if fallite:
            st.error("Non inviate:")
            st.write("\n".join(f"- {f}" for f in fallite))
        return inviate

    # ---------- invio ai partecipanti ----------
    st.subheader("Invia la registrazione")

    if lessons.empty:
        st.info("Nessuna lezione in calendario.")
    else:
        solo_online = st.checkbox(
            "Solo lezioni online", value=True, key="rec_solo_online"
        )
        passate = lessons[lessons["date"] <= date.today()]
        if solo_online:
            passate = passate[passate["mode"] == "online"]
        passate = passate.sort_values(["date", "time"], ascending=False)

        if passate.empty:
            st.info("Nessuna lezione passata con questi filtri.")
        else:
            def _label_rec(lid: str) -> str:
                r = passate[passate["lesson_id"] == lid].iloc[0]
                return (
                    f"{r['title']} · {r['date'].strftime('%d/%m/%Y')} "
                    f"ore {r['time']}"
                )

            with st.form("rec_link"):
                rec_lid = st.selectbox(
                    "Lezione",
                    options=list(passate["lesson_id"]),
                    format_func=_label_rec,
                    key="rec_lezione",
                )
                rec_link = st.text_input(
                    "Link YouTube",
                    placeholder="https://youtu.be/...",
                    key="rec_link_input",
                )
                genera = st.form_submit_button(
                    "Genera lista partecipanti", type="primary"
                )

            if genera:
                link = rec_link.strip()
                if not link.startswith("http") or "youtu" not in link:
                    st.error("Inserisci un link YouTube valido.")
                    st.session_state.pop("rec_attiva", None)
                else:
                    try:
                        data.set_recording(rec_lid, link)
                    except Exception as exc:
                        st.warning(f"Link non salvato sul foglio: {exc}")
                    st.session_state.rec_attiva = {
                        "lesson_id": rec_lid, "link": link
                    }

            attiva = st.session_state.get("rec_attiva")
            if attiva and attiva["lesson_id"] in set(passate["lesson_id"]):
                lez = passate[passate["lesson_id"] == attiva["lesson_id"]].iloc[0]
                categoria = nomi_cat.get(str(lez["category_id"]), lez["title"])
                giorno = lez["date"].strftime("%d/%m/%Y")

                if bookings.empty:
                    iscritti = pd.DataFrame(columns=["booking_id", "name", "email"])
                else:
                    iscritti = (
                        bookings[
                            (bookings["lesson_id"] == attiva["lesson_id"])
                            & (bookings["status"] != "cancelled")
                        ]
                        .drop_duplicates(subset="email")
                        .sort_values("name")
                    )

                st.divider()
                st.markdown(f"**{categoria} del {giorno}**")
                st.caption(
                    f"Oggetto: La registrazione di {categoria} del {giorno} è online"
                )

                if iscritti.empty:
                    st.info("Nessuna prenotazione attiva per questa lezione.")
                else:
                    with st.form("rec_invio"):
                        selezionati = []
                        for r in iscritti.itertuples(index=False):
                            chk = st.checkbox(
                                f"{r.name} ({r.email})",
                                value=True,
                                key=f"rec_chk_{attiva['lesson_id']}_{r.booking_id}",
                            )
                            if chk:
                                selezionati.append((r.email, r.name))
                        invia = st.form_submit_button("Invia mail", type="primary")

                    if invia:
                        if not selezionati:
                            st.warning("Nessuna persona selezionata.")
                        else:
                            _invia_registrazione(
                                selezionati, categoria, giorno, attiva["link"]
                            )

    # ---------- tabella registrazioni ----------
    st.divider()
    st.subheader("Registrazioni caricate")

    recordings = data.load_recordings()

    if recordings.empty:
        st.info("Nessuna registrazione caricata.")
    else:
        reg = recordings.merge(lessons, on="lesson_id", how="left")
        reg["categoria"] = (
            reg["category_id"].astype(str).map(nomi_cat).fillna(reg["title"])
        )
        reg["giorno"] = reg["date"].map(
            lambda d: d.strftime("%d/%m/%Y") if pd.notna(d) else "?"
        )
        reg = reg.sort_values(["date", "time"], ascending=False, na_position="last")

        st.dataframe(
            reg[["giorno", "time", "categoria", "url"]],
            column_config={
                "giorno": "data",
                "time": "ora",
                "url": st.column_config.LinkColumn("link"),
            },
            use_container_width=True, hide_index=True,
        )

        # ---------- invio ad altre persone ----------

        st.divider()
        st.subheader("Invia una registrazione ad altre persone")

        fonti = [
            df[["email", "name"]]
            for df in (bookings, payments, data.load_package_requests())
            if not df.empty
        ]
        utenti = (
            pd.concat(fonti, ignore_index=True)
            if fonti else pd.DataFrame(columns=["email", "name"])
        )
        utenti = utenti[utenti["email"].astype(str).str.contains("@")].copy()

        if utenti.empty:
            st.info("Nessun utente registrato.")
        elif categories.empty:
            st.warning("Crea prima almeno una categoria.")
        else:
            utenti["name"] = (
                utenti["name"].astype(str).str.strip().replace("", pd.NA)
            )
            utenti = (
                utenti.groupby("email", as_index=False)
                .agg(name=("name", "last"))
                .fillna({"name": ""})
                .sort_values("name")
            )
            nome_utente = dict(zip(utenti["email"], utenti["name"]))

            saldi_rec = data.balances_all(payments, bookings, lessons, categories)
            saldo_di = {
                (r.email, r.category_id): int(r.saldo)
                for r in saldi_rec.itertuples(index=False)
            }
            lista_cat = list(categories["category_id"])

            def _label_reg(lid: str) -> str:
                r = reg[reg["lesson_id"] == lid].iloc[0]
                return f"{r['categoria']} · {r['giorno']} ore {r['time']}"

            # ---------- invio a chi ha saldo positivo ----------
            if st.checkbox(
                "Invia lezione a persone con saldo positivo", key="rec_pos_on"
            ):
                cat_pos = st.selectbox(
                    "Categoria",
                    options=lista_cat,
                    format_func=lambda c: nomi_cat.get(c, c),
                    key="rec_pos_cat",
                )
                lid_pos = st.selectbox(
                    "Registrazione da inviare",
                    options=list(reg["lesson_id"]),
                    format_func=_label_reg,
                    key="rec_pos_lez",
                )

                # esclude chi era prenotato alla lezione o ha già ricevuto la registrazione
                esclusi = set()
                if not bookings.empty:
                    esclusi |= set(
                        bookings.loc[
                            (bookings["lesson_id"] == lid_pos)
                            & (bookings["status"] != "cancelled"),
                            "email",
                        ]
                    )
                gia_inviati = data.load_recording_shares()
                if not gia_inviati.empty:
                    esclusi |= set(
                        gia_inviati.loc[gia_inviati["lesson_id"] == lid_pos, "email"]
                    )

                positivi = saldi_rec[
                    (saldi_rec["category_id"] == cat_pos) & (saldi_rec["saldo"] > 0)
                ]
                n_esclusi = int(positivi["email"].isin(esclusi).sum())
                positivi = (
                    positivi[~positivi["email"].isin(esclusi)]
                    .sort_values("name")
                    .reset_index(drop=True)
                )

                if n_esclusi:
                    st.caption(
                        f"{n_esclusi} persone escluse perché hanno partecipato "
                        f"alla lezione o hanno già ricevuto la registrazione."
                    )

                if positivi.empty:
                    st.info("Nessuna persona a cui inviarla in questa categoria.")
                else:
                    tabella = positivi.assign(invia=True)[
                        ["invia", "name", "email", "saldo"]
                    ].rename(columns={"name": "persona"})

                    modificata = st.data_editor(
                        tabella,
                        column_config={
                            "invia": st.column_config.CheckboxColumn(
                                "invia", default=True
                            ),
                        },
                        disabled=["persona", "email", "saldo"],
                        hide_index=True,
                        use_container_width=True,
                        key=f"rec_pos_tab_{cat_pos}_{lid_pos}",
                    )
                    scelti = modificata[modificata["invia"]]

                    non_scalare = st.checkbox(
                        "Non scalare la lezione", value=False, key="rec_pos_no_scala"
                    )
                    nome_cat_pos = nomi_cat.get(cat_pos, cat_pos)
                    st.caption(
                        f"{len(scelti)} persone selezionate · "
                        + (
                            "nessuna lezione verrà scalata"
                            if non_scalare
                            else f"verrà scalata 1 lezione di {nome_cat_pos}"
                        )
                    )

                    if st.button("Invia mail", type="primary", key="rec_pos_btn"):
                        if scelti.empty:
                            st.warning("Nessuna persona selezionata.")
                        else:
                            r_pos = reg[reg["lesson_id"] == lid_pos].iloc[0]
                            inviati = _invia_registrazione(
                                list(zip(scelti["email"], scelti["persona"])),
                                r_pos["categoria"], r_pos["giorno"], r_pos["url"],
                                altri=True,
                            )
                            if inviati:
                                try:
                                    data.add_recording_shares(
                                        lid_pos, inviati,
                                        "" if non_scalare else cat_pos,
                                    )
                                    st.caption(
                                        "Invio registrato, nessuna lezione scalata."
                                        if non_scalare
                                        else f"Scalata 1 lezione di {nome_cat_pos} "
                                        f"a {len(inviati)} persone."
                                    )
                                except Exception as exc:
                                    st.warning(
                                        f"Mail inviate, ma l'invio non è stato "
                                        f"registrato sul foglio: {exc}"
                                    )

            st.divider()

            # ---------- invio manuale ----------
            lid_altri = st.selectbox(
                "Registrazione",
                options=list(reg["lesson_id"]),
                format_func=_label_reg,
                key="rec_altri_lez",
            )
            r_sel = reg[reg["lesson_id"] == lid_altri].iloc[0]

            cat_lez = str(r_sel["category_id"])
            cat_addebito = st.selectbox(
                "Scala 1 lezione dal saldo di",
                options=lista_cat,
                index=lista_cat.index(cat_lez) if cat_lez in lista_cat else 0,
                format_func=lambda c: nomi_cat.get(c, c),
                key=f"rec_altri_cat_{lid_altri}",
            )

            def _label_dest(e: str) -> str:
                nome = nome_utente.get(e, "")
                chi = f"{nome} ({e})" if nome else e
                return f"{chi} · saldo {saldo_di.get((e, cat_addebito), 0)}"

            dest = st.multiselect(
                "Destinatari",
                options=list(utenti["email"]),
                format_func=_label_dest,
                placeholder="Aggiungi persone",
                key="rec_altri_dest",
            )

            non_scalare_altri = st.checkbox(
                "Non scalare la lezione", value=False, key="rec_altri_no_scala"
            )
            nome_cat_addebito = nomi_cat.get(cat_addebito, cat_addebito)
            st.caption(
                f"{len(dest)} persone selezionate · "
                + (
                    "nessuna lezione verrà scalata"
                    if non_scalare_altri
                    else f"verrà scalata 1 lezione di {nome_cat_addebito}"
                )
            )

            if st.button("Invia mail", type="primary", key="rec_altri_btn"):
                if not dest:
                    st.warning("Nessuna persona selezionata.")
                else:
                    inviati = _invia_registrazione(
                        [(e, nome_utente.get(e, "")) for e in dest],
                        r_sel["categoria"], r_sel["giorno"], r_sel["url"],
                        altri=True,
                    )
                    if inviati:
                        try:
                            data.add_recording_shares(
                                lid_altri, inviati,
                                "" if non_scalare_altri else cat_addebito,
                            )
                            st.caption(
                                "Invio registrato, nessuna lezione scalata."
                                if non_scalare_altri
                                else f"Scalata 1 lezione di {nome_cat_addebito} "
                                f"a {len(inviati)} persone."
                            )
                        except Exception as exc:
                            st.warning(
                                f"Mail inviate, ma l'invio non è stato "
                                f"registrato sul foglio: {exc}"
                            )

    # ---------- storico invii extra ----------
    st.divider()
    st.subheader("Registrazioni inviate ad altre persone")

    shares = data.load_recording_shares()

    if shares.empty:
        st.info("Nessun invio registrato.")
    else:
        sh = shares.merge(
            lessons[["lesson_id", "date", "time", "title", "category_id"]]
            .rename(columns={"category_id": "cat_lezione"}),
            on="lesson_id", how="left",
        )
        sh["categoria"] = (
            sh["cat_lezione"].astype(str).map(nomi_cat)
            .fillna(sh["title"]).fillna("—")
        )
        sh["scalata da"] = sh["category_id"].map(nomi_cat).fillna("—")
        sh["lezione"] = sh.apply(
            lambda r: (
                f"{r['categoria']} · {r['date'].strftime('%d/%m/%Y')} ore {r['time']}"
                if pd.notna(r["date"]) else f"{r['categoria']} · lezione eliminata"
            ),
            axis=1,
        )
        sh["inviata il"] = (
            pd.to_datetime(sh["timestamp"], errors="coerce")
            .dt.strftime("%d/%m/%Y %H:%M").fillna(sh["timestamp"])
        )
        sh = sh.sort_values(
            ["date", "time", "name"], ascending=[False, False, True],
            na_position="last",
        )

        c1, c2 = st.columns(2)
        c1.metric("Invii totali", len(sh))
        c2.metric("Persone", sh["email"].nunique())

        st.markdown("**Per persona e categoria**")
        saldi_now = data.balances_all(payments, bookings, lessons, categories)
        saldo_now = {
            (r.email, r.category_id): int(r.saldo)
            for r in saldi_now.itertuples(index=False)
        }
        per_persona = (
            sh.groupby(["email", "category_id"], as_index=False)
            .agg(persona=("name", "last"), registrazioni=("lesson_id", "count"))
        )
        per_persona["categoria"] = (
            per_persona["category_id"].map(nomi_cat).fillna("— non scalata —")
        )
        per_persona["saldo"] = pd.Series(
            [
                saldo_now.get((e, c)) if c else None
                for e, c in zip(per_persona["email"], per_persona["category_id"])
            ],
            dtype="Int64",
        )
        per_persona = per_persona.sort_values(["persona", "categoria"])
        st.dataframe(
            per_persona[["persona", "email", "categoria", "registrazioni", "saldo"]]
            .rename(columns={"registrazioni": "registrazioni"}),
            use_container_width=True, hide_index=True,
        )

        st.markdown("**Per lezione**")
        opz_lez = ["tutte"] + list(dict.fromkeys(sh["lesson_id"]))
        filtro_lez = st.selectbox(
            "Lezione",
            options=opz_lez,
            format_func=lambda l: (
                "Tutte le lezioni" if l == "tutte"
                else sh.loc[sh["lesson_id"] == l, "lezione"].iloc[0]
            ),
            key="share_filtro_lez",
        )
        vd = sh if filtro_lez == "tutte" else sh[sh["lesson_id"] == filtro_lez]
        st.caption(f"{len(vd)} invii")
        st.dataframe(
            vd[["lezione", "name", "email", "scalata da", "inviata il"]].rename(
                columns={"name": "persona"}
            ),
            use_container_width=True, hide_index=True,
        )

# =============================================================
# PACCHETTI REGISTRAZIONI
# =============================================================
with tab_pack:
    st.subheader("Categorie in vendita")
    st.caption(
        "Le categorie selezionate compaiono nella pagina «Acquista un pacchetto "
        "di lezioni registrate», con prezzo e numero di lezioni del pacchetto."
    )

    if categories.empty:
        st.warning("Crea prima almeno una categoria.")
    else:
        in_vendita = data.load_recording_packages()
        lista_pack = list(categories["category_id"])

        def _label_pack(cid: str) -> str:
            r = categories[categories["category_id"] == cid].iloc[0]
            return (
                f"{r['name']} · {int(r['package_credits'])} lezioni · "
                f"€ {r['price_package']:.2f}"
            )

        scelte = st.multiselect(
            "Categorie",
            options=lista_pack,
            default=[c for c in in_vendita if c in lista_pack],
            format_func=_label_pack,
            placeholder="Scegli le categorie in vendita",
            key="pack_cats",
        )

        senza_prezzo = [
            c for c in scelte
            if categories.loc[categories["category_id"] == c, "price_package"].iloc[0] <= 0
            or categories.loc[categories["category_id"] == c, "package_credits"].iloc[0] <= 0
        ]
        if senza_prezzo:
            st.warning(
                "Queste categorie non hanno prezzo o numero di lezioni del "
                "pacchetto e non verranno mostrate: "
                + ", ".join(_label_pack(c) for c in senza_prezzo)
            )

        if st.button("Salva", type="primary", key="pack_save"):
            try:
                data.set_recording_packages(scelte)
                st.success("Categorie in vendita aggiornate.")
                st.rerun()
            except Exception as exc:
                st.error(f"Non sono riuscito a salvare: {exc}")