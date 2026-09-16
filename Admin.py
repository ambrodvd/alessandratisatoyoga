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

PAYPAL = st.secrets.get("paypal_me", "")

tab_lezioni, tab_pren, tab_persone = st.tabs(
    ["Lezioni", "Prenotazioni", "Persone e pagamenti"]
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
            ok_del = st.checkbox("Seleziona la casella se sei sicura di voler cancellare", key="cat_del_ok")
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
                conferma = st.checkbox("Seleziona la casella se sei sicura di voler cancellare", key="les_del_ok")
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

        st.divider()
        st.subheader("Annulla una prenotazione")
        st.divider()
        st.subheader("Annulla una prenotazione")

        annullabili = merged[merged["status"] != "cancelled"].copy()
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
            conferma_ann = st.checkbox("Seleziona la casella se sei sicura di voler cancellare", key="pren_conferma")

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
            balances[["name", "categoria", "acquistati", "usati", "saldo", "email"]]
            .rename(columns={"name": "persona", "usati": "lezioni usate"}),
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