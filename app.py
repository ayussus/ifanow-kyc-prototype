"""IFANOW · KYC/AML onboarding prototype (Streamlit).

A clickable demo of the design in the deck: PAN-first discovery, a progressive
journey with a live Readiness Passport, an 8-stage rules engine, and an advisor
workspace with a KYC health scan. All data is fictional; no real APIs are called.
"""
from datetime import datetime

import pandas as pd
import streamlit as st

from engine import rules
from engine.data import ADVISOR, CLIENT_BOOK_EXTRA, PERSONAS, fetch_discovery, load_persona
from engine.matching import name_score, match_action
from engine.pan import validate_pan

st.set_page_config(page_title="IFANOW · KYC Onboarding Prototype", page_icon="🟢", layout="wide")

G, NAVY, OCEAN, AMBER, CORAL = "#02B875", "#111D3A", "#004164", "#E9A91F", "#E8594A"
st.markdown(f"""
<style>
  .block-container {{padding-top: 1.6rem; padding-bottom: 2rem;}}
  .pill {{display:inline-block;padding:2px 10px;border-radius:12px;font-size:0.8rem;font-weight:600;color:#fff;margin-right:4px}}
  .ok {{background:{G}}} .warn {{background:{AMBER}}} .fail {{background:{CORAL}}} .pending {{background:#9AA5A1}} .info {{background:{OCEAN}}}
  .card {{border:1px solid #D5DEDA;border-radius:10px;padding:12px 14px;margin-bottom:10px;background:#fff}}
  .passport {{border:2px solid {G};border-radius:14px;padding:14px 16px;background:#F6FFFD}}
  .muted {{color:#6B6A70;font-size:0.85rem}}
  .big {{font-size:1.35rem;font-weight:700;color:{NAVY}}}
  .step-done {{color:{G};font-weight:700}} .step-now {{color:{NAVY};font-weight:700}} .step-todo {{color:#9AA5A1}}
</style>""", unsafe_allow_html=True)

STEPS = ["0 · PAN discovery", "1 · Identity core", "2 · Segment pack", "3 · Tier 1: MF-ready", "4 · Tier 2: PMS-ready"]
OTP = "123456"

# ------------------------------------------------------------------ state
ss = st.session_state
ss.setdefault("profiles", {})
ss.setdefault("cur", None)
ss.setdefault("step", 0)
ss.setdefault("log", [])
ss.setdefault("mode", "Self-serve (investor)")
ss.setdefault("scan_done", False)
ss.setdefault("new_clients", [])
ss.setdefault("nav", "Overview")


def log(event, actor=None):
    ss.log.insert(0, {"time": datetime.now().strftime("%H:%M:%S"),
                      "actor": actor or ("Advisor" if ss.mode.startswith("Advisor") else "Investor"),
                      "pan": ss.cur or "-", "event": event})


def pill(text, kind):
    return f'<span class="pill {kind}">{text}</span>'


def profile():
    return ss.profiles.get(ss.cur)


def open_pan(pan, step=0):
    v = validate_pan(pan)
    if not v["valid"]:
        return v
    if pan not in ss.profiles:
        p = load_persona(pan)
        p.update({"segment": v["segment"], "holder_label": v["holder_label"], "declarations": set()})
        ss.profiles[pan] = p
    ss.cur, ss.step = pan, step
    log(f"Opened journey for {pan}")
    return v


def goto(page, pan=None):
    """Button callback: runs before the rerun, so it can set the nav widget's state."""
    if pan:
        open_pan(pan)
    ss.nav = page


# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.markdown(f"<div class='big'>IFANOW <span style='color:{G}'>KYC</span></div>"
                "<div class='muted'>Onboarding prototype · demo data only</div>", unsafe_allow_html=True)
    st.radio("Go to", ["Overview", "Investor journey", "Advisor workspace", "Engine inspector"], key="nav")
    st.divider()
    ss.mode = st.radio("Onboarding mode", ["Self-serve (investor)", "Advisor-assisted"],
                       index=0 if ss.mode.startswith("Self") else 1,
                       help="Same engine, different front door. Advisor mode adds pre-fill, consent on the investor's device and a contact lock.")
    if ss.cur:
        st.caption(f"Active investor: **{profile()['name']}** ({ss.cur})")
    st.divider()
    st.caption(f"Demo OTP for every step: **{OTP}**")
    if st.button("Reset demo", use_container_width=True):
        for k in list(ss.keys()):
            del ss[k]
        st.rerun()


# ------------------------------------------------------------------ passport
def passport(p):
    mf, pms, rk = rules.mf_gaps(p), rules.pms_gaps(p), rules.risk(p)
    kra = rules.kra_effective(p)
    kra_kind = "ok" if kra.startswith("Validated") else ("warn" if kra == "Registered" else "fail")
    with st.container(border=True):
        st.markdown(f"<div class='big'>🛂 Readiness Passport</div><div class='muted'>{p['name']} · {p['holder_label']}"
                    f"{' · NRI (' + p['country'] + ')' if p['residency'] == 'nri' else ''}</div>", unsafe_allow_html=True)
        st.markdown("**KYC health** " + pill("KRA " + kra, kra_kind) +
                    pill("CKYC " + ("linked" if p["ckyc"]["found"] else "new"), "info") +
                    pill(f"Risk {rk['band']}", {"Low": "ok", "Medium": "warn", "High": "fail"}[rk["band"]]), unsafe_allow_html=True)
        for label, gaps, extra in [("Mutual funds", mf, rules.us_amc_note(p)), ("PMS", pms, None)]:
            st.divider()
            if not gaps:
                st.markdown(f"**{label}** " + pill("✓ Ready", "ok"), unsafe_allow_html=True)
                if label == "PMS" and p["pms_pack_sent"]:
                    st.caption("Pre-verified pack sent to the PMS provider.")
            else:
                st.markdown(f"**{label}** " + pill(f"{len(gaps)} step{'s' if len(gaps) > 1 else ''} left", "warn"), unsafe_allow_html=True)
                items = "".join(f"• {g}<br>" for g, _ in gaps[:5])
                more = f"<i>+ {len(gaps) - 5} more</i>" if len(gaps) > 5 else ""
                st.markdown(f"<div class='muted'>{items}{more}</div>", unsafe_allow_html=True)
            if extra:
                st.caption("⚠ " + extra)
        st.divider()
        st.markdown("**Bonds / AIF** " + pill("Later · same profile", "pending"), unsafe_allow_html=True)


# ================================================================== OVERVIEW
def page_overview():
    st.title("KYC/AML onboarding: working prototype")
    st.markdown("**Thesis:** KYC is not a one-time gate; it's a live *readiness* state per asset. "
                "This demo shows one engine behind two front doors, the investor storefront and the advisor workspace, "
                "and a **Readiness Passport** that shows what each investor can invest in *before* they try.")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown("<div class='card'><b>1 · Investor journey</b><br><span class='muted'>PAN-first discovery → identity → segment pack → MF tier → PMS tier, "
                    "with the Passport updating live.</span></div>", unsafe_allow_html=True)
    with c2:
        st.markdown("<div class='card'><b>2 · Advisor workspace</b><br><span class='muted'>KYC health scan of the client book, exceptions inbox with EN/HI fixes, "
                    "and new-client onboarding with a contact lock.</span></div>", unsafe_allow_html=True)
    with c3:
        st.markdown("<div class='card'><b>3 · Engine inspector</b><br><span class='muted'>The 8 stages, risk scoring with what-if toggles, "
                    "the owner tree and a name-matching playground.</span></div>", unsafe_allow_html=True)

    st.subheader("Try a demo investor")
    st.caption("Each persona exercises a different part of the design. Pick one to open their journey.")
    rows = []
    for pan, p in PERSONAS.items():
        rows.append({"PAN": pan, "Name": p["name"], "Type (from PAN)": validate_pan(pan)["holder_label"], "What it shows": p["_story"]})
    st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    cols = st.columns(4)
    for i, (pan, p) in enumerate(PERSONAS.items()):
        cols[i % 4].button(f"Open {p['name'].title()}", key=f"ov_{pan}", use_container_width=True,
                           on_click=goto, args=("Investor journey", pan))

    st.subheader("Suggested 3-minute demo")
    st.markdown("""
1. **Advisor workspace → Run KYC health scan.** See who is On Hold or Registered across the client book, with a ready-to-send fix in English or Hindi.
2. **Open Venkatesh Rao (retiree).** His Aadhaar mobile is dead, so the OTP route fails and the engine offers Aadhaar XML or advisor-led video KYC instead.
3. **Open Ramesh K Iyer.** Watch the name checks: the bank name is auto-accepted, Aadhaar needs a one-line declaration, and the demat mismatch blocks **only PMS**.
4. **Open Meera Shah.** PMS interest was tagged by her advisor, so Tier 2 is asked early; Account Aggregator verifies source of funds and a pre-verified pack goes to the PMS firm.
5. **Engine inspector.** Toggle PEP or sanctions and watch the risk band and routing change.
""")
    st.info("Prototype only: every PAN, name and number is fictional, and registry calls (ITD, KRA, CKYC, DigiLocker, penny drop, "
            "Account Aggregator) are simulated. In production these are API integrations; the rules layer stays the same.")


# ================================================================== JOURNEY
def page_journey():
    st.title("Investor journey")
    if ss.mode.startswith("Advisor"):
        st.info(f"**Advisor-assisted mode.** {ADVISOR['name']} ({ADVISOR['firm']}) is filling this in. "
                "The investor approves on their own phone (OTP / eSign); the advisor's own contact details are locked out.")

    with st.expander("Choose an investor", expanded=ss.cur is None):
        c1, c2 = st.columns([2, 1])
        options = {f"{p['name'].title()} · {pan}": pan for pan, p in PERSONAS.items()}
        pick = c1.selectbox("Demo persona", list(options.keys()))
        c1.caption(PERSONAS[options[pick]]["_story"])
        if c1.button("Start with this persona", type="primary"):
            open_pan(options[pick]); st.rerun()
        own = c2.text_input("…or type any PAN", placeholder="ABCPE1234F")
        if c2.button("Start with this PAN"):
            v = open_pan(own.strip().upper())
            if not v["valid"]:
                c2.error(v["error"])
            else:
                st.rerun()

    p = profile()
    if not p:
        st.caption("Pick an investor to begin.")
        return

    # progress header
    marks = []
    for i, s_ in enumerate(STEPS):
        cls = "step-done" if i < ss.step else ("step-now" if i == ss.step else "step-todo")
        marks.append(f"<span class='{cls}'>{s_}</span>")
    st.markdown(" &nbsp;→&nbsp; ".join(marks), unsafe_allow_html=True)
    st.progress((ss.step + 1) / len(STEPS))

    left, right = st.columns([2.1, 1])
    with right:
        passport(p)
    with left:
        [step0, step1, step2, step3, step4][ss.step](p)
        st.markdown("")
        b1, _, b2 = st.columns([1, 2, 1])
        if ss.step > 0 and b1.button("← Back", use_container_width=True):
            ss.step -= 1; st.rerun()
        if ss.step < len(STEPS) - 1 and b2.button("Next →", type="primary", use_container_width=True):
            ss.step += 1; st.rerun()


def step0(p):
    st.subheader("Step 0 · PAN-first discovery")
    st.markdown(f"PAN **{p['pan']}** → 4th character **'{p['pan'][3]}'** = **{p['holder_label']}**. "
                "The journey attaches the right segment pack automatically.")
    disc = fetch_discovery(p)
    st.markdown("<div class='card'>" + "".join(f"<b>{k}</b>: {v}<br>" for k, v in disc.items()) + "</div>", unsafe_allow_html=True)
    st.caption("Simulated calls to the Income Tax Dept, KRA, CKYC registry and RTAs (CAS). We start from what already exists.")

    kra = p["kra"]["status"]
    key = None
    if kra == "On Hold":
        key = "pan_aadhaar" if not p["itd"]["pan_aadhaar_linked"] else "on_hold_contact"
        st.error("KYC **On Hold**: no transactions are possible today. We'll fix it inside this journey.")
    elif kra == "Registered":
        key = "registered"
        st.warning("KYC **Registered**: fine for existing fund houses, but a new fund house needs re-validation. One Aadhaar check fixes it.")
    elif kra == "Not found":
        key = "not_found"
        st.info("No KYC on record: we'll create it and upload to KRA and CKYC at the end.")
    else:
        st.success("KYC **Validated** at KRA: identity data is reused, with nothing to upload.")
    if key:
        lang = st.radio("Explain it to the investor in", ["English", "हिन्दी"], horizontal=True, key="lang0")
        st.markdown(f"> {rules.EXPLAIN[key][0 if lang == 'English' else 1]}")

    signals = []
    if p["advisor_tag_pms"]:
        signals.append("advisor tagged PMS interest")
    if p["income_lakh"] >= 50:
        signals.append(f"income band ₹{p['income_lakh']}L")
    if p["planned_pms_lakh"] >= 50:
        signals.append(f"plans ₹{p['planned_pms_lakh']}L")
    if signals:
        st.markdown(pill("Predictive trigger", "info") + f" PMS likely ({', '.join(signals)}), so Tier-2 questions will be asked in this session, not at checkout.",
                    unsafe_allow_html=True)
    if rules.us_amc_note(p):
        st.warning(rules.us_amc_note(p))
    packs = []
    if p["residency"] == "nri":
        packs.append("NRI / OCI")
    if rules.is_hni(p) and not rules.is_entity(p):
        packs.append("HNI")
    if p["segment"] == "huf":
        packs.append("HUF")
    if p["segment"] == "corporate":
        packs.append("Corporate")
    if p["occupation"] == "Retired":
        packs.append("Retiree (assisted by default)")
    st.markdown("**Segment packs attached:** " + (", ".join(packs) if packs else "none needed (baseline journey)"))


def step1(p):
    st.subheader("Step 1 · Identity core")
    ent = rules.is_entity(p)
    if ent:
        st.caption(f"For a {p['holder_label']}, identity is verified for the authorised signatory / Karta, plus entity documents in Step 2.")

    # PAN-Aadhaar link
    if not ent:
        if p["itd"]["pan_aadhaar_linked"]:
            st.markdown(pill("✓", "ok") + " PAN–Aadhaar link confirmed with the Income Tax Dept", unsafe_allow_html=True)
        else:
            st.error("PAN is not linked to Aadhaar. KRA can't validate this KYC.")
            if st.button("I've linked it on the Income Tax portal: recheck"):
                p["itd"]["pan_aadhaar_linked"] = True; log("PAN–Aadhaar link rechecked: linked"); st.rerun()

    # Aadhaar / DigiLocker
    with st.container(border=True):
        st.markdown("**Aadhaar via DigiLocker**" + (" (Karta / signatory)" if ent else ""))
        a = p["aadhaar"]
        if a["verified"] or a["xml_fallback"]:
            st.markdown(pill("✓", "ok") + (" Fetched from DigiLocker" if a["verified"] else " Verified via fallback (Aadhaar XML / video KYC)") +
                        f": name on Aadhaar **{a['name'] or '-'}**", unsafe_allow_html=True)
        else:
            if st.button("Fetch from DigiLocker"):
                if a["mobile_active"]:
                    a["verified"] = True; log("DigiLocker fetch: success")
                else:
                    ss["dl_fail_" + p["pan"]] = True; log("DigiLocker OTP failed: Aadhaar-linked mobile inactive")
                st.rerun()
            if ss.get("dl_fail_" + p["pan"]) and not a["mobile_active"]:
                st.error("The OTP couldn't be delivered: the mobile number linked to Aadhaar is no longer active. No dead end, pick a fallback:")
                f1, f2 = st.columns(2)
                if f1.button("Upload offline Aadhaar XML"):
                    a["xml_fallback"] = True; log("Aadhaar offline XML accepted (fallback)"); st.rerun()
                if f2.button("Video KYC with my advisor (VIPV)"):
                    a["xml_fallback"] = True; log("Video IPV completed with advisor (fallback)", "Advisor"); st.rerun()

    if not ent:
        with st.container(border=True):
            st.markdown("**Selfie: liveness + face match**")
            if p["liveness"]:
                st.markdown(pill("✓", "ok") + f" Live person · face match with Aadhaar photo {p['face_match']:.2f}", unsafe_allow_html=True)
            elif st.button("Take selfie"):
                p["liveness"], p["face_match"] = True, 0.96; log("Liveness passed, face match 0.96"); st.rerun()

    with st.container(border=True):
        st.markdown("**Contact verification (OTP)**")
        c = p["contact"]
        if ss.mode.startswith("Advisor") and not c["mobile_verified"]:
            newm = st.text_input("Investor mobile (advisor can edit)", c["mobile"], key=f"mob_{p['pan']}")
            if newm != c["mobile"]:
                if newm.strip() in (ADVISOR["mobile"], "+91" + ADVISOR["mobile"]):
                    st.error("🔒 Contact lock: this is the advisor's own number. A client's KYC must carry the client's own contact details.")
                    log("Blocked: advisor tried to use own mobile (contact lock)", "Advisor")
                else:
                    c["mobile"] = newm.strip()
        m1, m2 = st.columns(2)
        if c["mobile_verified"]:
            m1.markdown(pill("✓", "ok") + f" Mobile {c['mobile']}", unsafe_allow_html=True)
        else:
            otp = m1.text_input(f"OTP sent to {c['mobile']}" + (" (investor's phone)" if ss.mode.startswith("Advisor") else ""), key=f"otpm_{p['pan']}")
            if otp:
                if otp == OTP:
                    c["mobile_verified"] = True; log("Mobile OTP verified", "Investor"); st.rerun()
                else:
                    m1.error("Wrong OTP (demo OTP is 123456)")
        if not c["email"]:
            m2.caption("No email on record; mobile alone is accepted.")
        elif c["email_verified"]:
            m2.markdown(pill("✓", "ok") + f" Email {c['email']}", unsafe_allow_html=True)
        else:
            otp = m2.text_input(f"OTP sent to {c['email']}", key=f"otpe_{p['pan']}")
            if otp:
                if otp == OTP:
                    c["email_verified"] = True; log("Email OTP verified", "Investor"); st.rerun()
                else:
                    m2.error("Wrong OTP (demo OTP is 123456)")

    nm = [r for r in rules.name_checks(p) if r["source"] == "Aadhaar"]
    if nm:
        name_table(p, nm)
    if not [g for g in rules.core_gaps(p) if not g[0].startswith("Complete segment")]:
        if p["kra"]["status"] != "Validated":
            st.success("Identity core complete: KRA record will be (re)validated and uploaded to CKYC within 7 days.")
        else:
            st.success("Identity core complete.")


def name_table(p, rows):
    st.markdown(f"**Name reconciliation** against PAN name **{p['name']}**")
    for r in rows:
        kind = "ok" if r["resolved"] else r["level"]
        c1, c2 = st.columns([3, 1.3])
        c1.markdown(pill(f"{r['score']:.2f}", kind) + f" **{r['source']}**: {r['name']}<br><span class='muted'>{r['action']}</span>",
                    unsafe_allow_html=True)
        if r["level"] == "warn" and not r["resolved"]:
            if c2.button("Sign self-declaration", key=f"decl_{r['source']}"):
                p["declarations"].add(r["source"]); log(f"Self-declaration signed for {r['source']} name"); st.rerun()
        if r["level"] == "fail" and r["source"] == "Demat":
            if c2.button("Simulate: DP corrected name", key="dpfix"):
                p["demat"]["holder_name"] = p["name"]; log("DP updated demat holder name"); st.rerun()
        if r["level"] == "warn" and r["resolved"]:
            c2.caption("Declaration on file ✓")


def step2(p):
    st.subheader("Step 2 · Segment pack")
    if not rules.needs_segment_pack(p):
        st.success("No extra pack needed: this is the baseline resident journey.")
        p["segment_pack_done"] = True
        return
    ready = True
    if p["residency"] == "nri":
        with st.container(border=True):
            st.markdown("**NRI / OCI pack**")
            c1, c2 = st.columns(2)
            p["passport"] = c1.text_input("Passport / OCI number", p["passport"] or "Z1234567")
            p["overseas_address"] = c2.text_input("Overseas address", p["overseas_address"] or "221 Market St, San Francisco, CA")
            acct = st.selectbox("Bank account to invest from", ["Savings", "NRE", "NRO"],
                                index=["Savings", "NRE", "NRO"].index(p["bank"]["account_type"]) if p["bank"]["account_type"] in ("Savings", "NRE", "NRO") else 0)
            p["bank"]["account_type"] = acct
            if acct == "Savings":
                st.error("NRIs can't invest from a resident savings account. Choose NRE (repatriable) or NRO.")
                ready = False
            if p["us_person"]:
                st.warning("US person under FATCA: the fund list is filtered to AMCs that accept US/Canada investors.")
    if rules.is_hni(p) and not rules.is_entity(p):
        with st.container(border=True):
            st.markdown("**HNI pack**")
            c1, c2 = st.columns(2)
            c1.selectbox("Main source of wealth", ["Business income", "Salary", "Inheritance", "Sale of property", "Investments"], key=f"sow_{p['pan']}")
            pep = c2.radio("Are you (or a close relative) a Politically Exposed Person?", ["No", "Yes"], index=1 if p["pep"] else 0, key=f"pep_{p['pan']}")
            if (pep == "Yes") != p["pep"]:
                p["pep"] = pep == "Yes"; log(f"PEP declaration: {pep}"); st.rerun()
            if p["pep"]:
                st.warning("PEP → Enhanced Due Diligence and senior approval (see risk band).")
    if p["segment"] == "huf":
        e = p["entity"]
        with st.container(border=True):
            st.markdown(f"**HUF pack** · Karta: {e['karta']}")
            for d in list(e["docs"]):
                e["docs"][d] = st.checkbox(d, e["docs"][d], key=f"hufdoc_{d}")
            df = pd.DataFrame(e["members"])
            df["kyc"] = df["kyc"].map({True: "✓ done", False: "pending"})
            st.dataframe(df.rename(columns={"name": "Member", "role": "Role", "kyc": "KYC"}), hide_index=True, use_container_width=True)
            st.caption("Minor coparceners are represented by the Karta as guardian; their own KYC is triggered at 18 (life-event flow).")
            ready &= all(e["docs"].values())
    if p["segment"] == "corporate":
        e = p["entity"]
        with st.container(border=True):
            st.markdown("**Corporate pack**")
            for d in list(e["docs"]):
                e["docs"][d] = st.checkbox(d, e["docs"][d], key=f"codoc_{d}")
            st.markdown("**Owner tree → natural persons with more than 10%** (traced through holding entities)")
            people = rules.owner_tree_people(e["owners"])
            for person in people:
                over = person["effective_pct"] > 10
                c1, c2 = st.columns([3, 1.2])
                c1.markdown(pill(f"{person['effective_pct']}%", "info" if over else "pending") + f" **{person['person']}**"
                            f"<br><span class='muted'>via {' + '.join(person['via'])}</span>", unsafe_allow_html=True)
                if over and not person["kyc"]:
                    ready = False
                    if c2.button(f"Send KYC link", key=f"bo_{person['person']}"):
                        for o in e["owners"]:
                            for sub in o.get("owners", []):
                                if sub["name"] == person["person"]:
                                    sub["kyc"] = True
                        log(f"Beneficial owner {person['person']} completed KYC via link"); st.rerun()
                elif over:
                    c2.markdown(pill("KYC ✓", "ok"), unsafe_allow_html=True)
            st.caption("Minority holders below 10% aren't beneficial owners under the PML Rules and don't need individual KYC.")
            ready &= all(e["docs"].values())
    if p["segment_pack_done"]:
        st.success("Segment pack complete.")
    elif st.button("Complete segment pack", type="primary", disabled=not ready):
        p["segment_pack_done"] = True; log("Segment pack completed"); st.rerun()
    if not ready:
        st.caption("Finish the red items above to complete the pack.")


def step3(p):
    st.subheader("Step 3 · Tier 1: mutual-fund ready")
    with st.container(border=True):
        st.markdown("**FATCA / CRS self-certification**")
        if p["fatca_done"]:
            st.markdown(pill("✓", "ok") + " Declared", unsafe_allow_html=True)
        else:
            c1, c2 = st.columns(2)
            c1.selectbox("Country of tax residence", ["India", "United States", "United Kingdom", "UAE", "Other"],
                         index=1 if p["us_person"] else 0, key=f"fatca_c_{p['pan']}")
            if p["us_person"]:
                c2.text_input("US TIN / SSN (demo, not stored)", "000-00-0000", key=f"tin_{p['pan']}")
            if st.button("Submit declaration"):
                p["fatca_done"] = True; log("FATCA/CRS self-certification submitted"); st.rerun()
    if not rules.is_entity(p):
        with st.container(border=True):
            st.markdown("**Nominee**")
            if p["nominee_done"]:
                st.markdown(pill("✓", "ok") + " Recorded", unsafe_allow_html=True)
            else:
                c1, c2, c3 = st.columns([2, 1.2, 1])
                c1.text_input("Nominee name", "", key=f"nom_{p['pan']}")
                c2.selectbox("Relationship", ["Spouse", "Child", "Parent", "Sibling", "Other"], key=f"rel_{p['pan']}")
                c3.number_input("Share %", 1, 100, 100, key=f"sh_{p['pan']}")
                b1, b2 = st.columns(2)
                if b1.button("Save nominee"):
                    p["nominee_done"] = True; log("Nominee added"); st.rerun()
                if b2.button("Opt out (with declaration)"):
                    p["nominee_done"] = True; log("Nomination opt-out declared"); st.rerun()
    with st.container(border=True):
        st.markdown(f"**Bank verification (penny drop)** · {p['bank']['account_type']} account")
        if p["bank"]["verified"]:
            st.markdown(pill("✓", "ok") + f" ₹1 credited · bank returned holder name **{p['bank']['holder_name']}**", unsafe_allow_html=True)
        elif st.button("Verify bank account"):
            p["bank"]["verified"] = True; log(f"Penny drop: holder name '{p['bank']['holder_name']}'"); st.rerun()
    nm = [r for r in rules.name_checks(p) if r["source"] in ("Aadhaar", "Bank")]
    if nm:
        name_table(p, nm)
    with st.container(border=True):
        st.markdown("**Platform registration (UCC on BSE StAR MF / NSE NMF, or MFU CAN)**")
        blockers = [g for g in rules.mf_gaps(p) if not g[0].startswith("Create UCC")]
        if p["ucc_created"]:
            st.markdown(pill("✓", "ok") + " UCC created on BSE StAR MF (demo)", unsafe_allow_html=True)
        else:
            if blockers:
                st.caption("Available once these are done: " + "; ".join(g[0] for g in blockers))
            if st.button("Create UCC", disabled=bool(blockers)):
                p["ucc_created"] = True; log("UCC created (BSE StAR MF)"); st.rerun()
    with st.container(border=True):
        st.markdown("**E-mandate for SIPs** (recommended, not required)")
        if p["mandate_done"]:
            st.markdown(pill("✓", "ok") + " NACH e-mandate registered", unsafe_allow_html=True)
        elif st.button("Set up e-mandate"):
            p["mandate_done"] = True; log("E-mandate registered"); st.rerun()
    if not rules.mf_gaps(p):
        st.balloons() if not ss.get(f"mfb_{p['pan']}") else None
        ss[f"mfb_{p['pan']}"] = True
        st.success("Mutual funds: ready. No rejection at the point of investing.")


def step4(p):
    st.subheader("Step 4 · Tier 2: PMS ready")
    st.caption("IFANOW's advisor distributes PMS; the portfolio manager opens the account. We prepare a complete, pre-verified pack.")
    amt = st.slider("Planned PMS investment (₹ lakh)", 0, 300, int(p["planned_pms_lakh"] or 50), step=5)
    if amt != p["planned_pms_lakh"]:
        p["planned_pms_lakh"] = amt
    if amt < rules.PMS_MIN_LAKH:
        st.error(f"SEBI minimum for PMS is ₹{rules.PMS_MIN_LAKH} lakh per client.")
    with st.container(border=True):
        st.markdown("**Demat account**")
        d = p["demat"]
        if d is None:
            p["demat"] = d = {"linked": False, "holder_name": p["name"], "dp": "CDSL", "ddpi": False}
        if d["linked"]:
            st.markdown(pill("✓", "ok") + f" Linked ({d['dp']}) · holder name **{d['holder_name']}**", unsafe_allow_html=True)
        elif st.button("Link demat (fetch holder details from depository)"):
            d["linked"] = True; log(f"Demat linked: holder '{d['holder_name']}'"); st.rerun()
        if d["linked"]:
            if d["ddpi"]:
                st.markdown(pill("✓", "ok") + " DDPI signed", unsafe_allow_html=True)
            elif st.button("eSign DDPI"):
                d["ddpi"] = True; log("DDPI eSigned"); st.rerun()
    nm = [r for r in rules.name_checks(p) if r["source"] == "Demat"]
    if nm:
        name_table(p, nm)
    with st.container(border=True):
        st.markdown("**Source of funds via Account Aggregator**")
        if p["source_of_funds_verified"]:
            st.markdown(pill("✓", "ok") + f" Consent logged · 12-month average balance ₹{p['aa_balance_lakh']}L · inflows consistent with declared income",
                        unsafe_allow_html=True)
        elif st.button("Approve one-time data share (AA consent)"):
            p["source_of_funds_verified"] = True
            p["aa_balance_lakh"] = round(max(amt, 50) * 1.4)
            log("Account Aggregator consent: bank data shared"); st.rerun()
        st.caption("No statement uploads: the bank shares data directly with the investor's consent (RBI Account Aggregator framework).")
    with st.container(border=True):
        st.markdown("**Suitability**")
        if p["suitability_done"]:
            st.markdown(pill("✓", "ok") + " Suitable for equity PMS", unsafe_allow_html=True)
        else:
            q1 = st.radio("Investment horizon", ["< 2 years", "2–5 years", "5+ years"], horizontal=True, key=f"q1_{p['pan']}")
            q2 = st.radio("If the portfolio fell 25% in a year, you would…", ["Sell", "Wait", "Invest more"], horizontal=True, key=f"q2_{p['pan']}")
            if st.button("Submit suitability"):
                if q1 == "< 2 years" or q2 == "Sell":
                    st.warning("Equity PMS looks unsuitable for this profile; the advisor will discuss alternatives.")
                    log("Suitability: flagged as unsuitable")
                else:
                    p["suitability_done"] = True; log("Suitability: suitable"); st.rerun()
    with st.container(border=True):
        st.markdown("**PMS agreement, MITC and fee acknowledgement**")
        if p["pms_agreement_signed"]:
            st.markdown(pill("✓", "ok") + " eSigned", unsafe_allow_html=True)
        else:
            ack = st.checkbox("I have read the Most Important Terms & Conditions and the multi-year fee illustration", key=f"mitc_{p['pan']}")
            if st.button("eSign agreement", disabled=not ack):
                p["pms_agreement_signed"] = True; log("PMS agreement + MITC eSigned"); st.rerun()
    gaps = rules.pms_gaps(p)
    if gaps:
        st.info("To finish PMS: " + "; ".join(g[0] for g in gaps))
    elif not p["pms_pack_sent"]:
        if st.button("Send pre-verified pack to PMS provider", type="primary"):
            p["pms_pack_sent"] = True; log("Pre-verified onboarding pack sent to PMS provider"); st.rerun()
    else:
        st.success("Pack sent. The PMS firm can activate in hours instead of days.")
        st.json({"investor": p["name"], "pan": p["pan"], "kra": "Validated", "ckyc_kin": p["ckyc"]["kin"] or "pending upload",
                 "demat": {"dp": p["demat"]["dp"], "ddpi": True}, "source_of_funds": "Account Aggregator (consent logged)",
                 "suitability": "suitable", "agreement": "eSigned with MITC", "risk_band": rules.risk(p)["band"],
                 "name_checks": [{r["source"]: r["score"]} for r in rules.name_checks(p)]})


# ================================================================== ADVISOR
def client_book():
    rows = []
    for pan in PERSONAS:
        p = ss.profiles.get(pan) or load_persona(pan)
        p.setdefault("segment", validate_pan(pan)["segment"])
        p.setdefault("declarations", set())
        p.setdefault("holder_label", validate_pan(pan)["holder_label"])
        mf, pms = rules.mf_gaps(p), rules.pms_gaps(p)
        st_ = p["kra"]["status"]
        if st_ == "On Hold":
            issue, key = f"KRA On Hold ({p['kra']['reason']}): all transactions blocked", ("pan_aadhaar" if not p["itd"]["pan_aadhaar_linked"] else "on_hold_contact")
        elif st_ == "Registered":
            issue, key = "KRA Registered: re-validate before investing with a new fund house", "registered"
        elif st_ == "Not found":
            issue, key = "No KYC on record", "not_found"
        elif rules.is_hni(p) and pms:
            issue, key = f"PMS interest but {len(pms)} steps missing", "pms_gap"
        else:
            issue, key = None, None
        rows.append({"PAN": pan, "Client": p["name"].title(), "KRA": st_, "MF": "Ready" if not mf else f"{len(mf)} steps left",
                     "PMS": "Ready" if not pms else ("Not needed" if not rules.is_hni(p) else f"{len(pms)} steps left"),
                     "Issue": issue or "-", "_key": key, "_persona": True})
    for c in CLIENT_BOOK_EXTRA:
        key = {"On Hold": "pan_aadhaar", "Registered": "registered"}.get(c["kra"])
        if c["issue"] and "Passport" in c["issue"]:
            key = "passport"
        rows.append({"PAN": c["pan"], "Client": c["name"].title(), "KRA": c["kra"], "MF": "Ready" if c["mf_ready"] else "Blocked",
                     "PMS": "Not needed", "Issue": c["issue"] or "-", "_key": key, "_persona": False})
    return rows


def page_advisor():
    st.title("Advisor workspace")
    st.caption(f"Signed in as **{ADVISOR['name']}** · {ADVISOR['firm']}")
    t1, t2, t3, t4 = st.tabs(["KYC health scan", "Exceptions inbox", "Pipeline", "Onboard new client"])

    with t1:
        st.markdown("Checks every client's PAN against the KRA and the readiness rules, so you **find problems before your clients do**. "
                    "It replaces downloading RTA mail-back reports and phoning clients one by one.")
        if st.button("Run KYC health scan on client book", type="primary"):
            with st.spinner("Checking 12 PANs against KRA, CKYC and readiness rules…"):
                import time; time.sleep(1.2)
            ss.scan_done = True; log("KYC health scan run on 12 clients", "Advisor")
        if ss.scan_done:
            rows = client_book()
            df = pd.DataFrame(rows)
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Clients scanned", len(df))
            k2.metric("On Hold (blocked)", int((df["KRA"] == "On Hold").sum()))
            k3.metric("Registered (partial)", int((df["KRA"] == "Registered").sum()))
            k4.metric("Need action", int((df["Issue"] != "-").sum()))
            only = st.toggle("Show only clients needing action", True)
            view = df[df["Issue"] != "-"] if only else df
            st.dataframe(view.drop(columns=["_key", "_persona"]), hide_index=True, use_container_width=True)
            st.markdown("#### Fix a client")
            needing = [r for r in rows if r["_key"]]
            sel = st.selectbox("Client", [f"{r['Client']} · {r['PAN']}" for r in needing])
            r = next(x for x in needing if f"{x['Client']} · {x['PAN']}" == sel)
            lang = st.radio("Message language", ["English", "हिन्दी"], horizontal=True, key="adv_lang")
            msg = rules.EXPLAIN[r["_key"]][0 if lang == "English" else 1]
            st.markdown(f"**Issue:** {r['Issue']}")
            st.code(f"Hi {r['Client'].split()[0]}, {msg}\nSecure link: https://kyc.ifanow.demo/fix/{r['PAN'][-4:]}", language=None)
            st.caption("Drafted by the exception explainer (template-based in this demo; LLM-drafted and rule-checked in production). Copy and send on WhatsApp.")
            if r["_persona"]:
                st.button("Open this client's journey", on_click=goto, args=("Investor journey", r["PAN"]))

    with t2:
        st.markdown("Every open exception across clients, most severe first, with the exact fix.")
        rows = client_book()
        sev = {"On Hold": 0, "Not found": 1, "Registered": 2}
        items = sorted([r for r in rows if r["_key"]], key=lambda r: sev.get(r["KRA"], 3))
        for r in items:
            kind = "fail" if r["KRA"] == "On Hold" else ("warn" if r["KRA"] in ("Registered", "Not found") else "info")
            with st.container(border=True):
                st.markdown(pill(r["KRA"], kind) + f" **{r['Client']}** ({r['PAN']})<br><span class='muted'>{r['Issue']}</span>",
                            unsafe_allow_html=True)
                st.caption("Suggested fix: " + rules.EXPLAIN[r["_key"]][0])

    with t3:
        rows = client_book()
        cols = st.columns(4)
        buckets = {"Blocked": [], "In progress": [], "MF-ready": [], "PMS pack sent": []}
        for r in rows:
            p = ss.profiles.get(r["PAN"])
            if p and p.get("pms_pack_sent"):
                buckets["PMS pack sent"].append(r)
            elif r["MF"] == "Ready":
                buckets["MF-ready"].append(r)
            elif r["KRA"] == "On Hold" or r["MF"] == "Blocked":
                buckets["Blocked"].append(r)
            else:
                buckets["In progress"].append(r)
        for c, (name, items) in zip(cols, buckets.items()):
            c.markdown(f"**{name}** ({len(items)})")
            for r in items:
                c.markdown(f"<div class='card'>{r['Client']}<br><span class='muted'>{r['PAN']} · KRA {r['KRA']}</span></div>", unsafe_allow_html=True)
        for nc in ss.new_clients:
            cols[1].markdown(f"<div class='card'>{nc['name']} (new)<br><span class='muted'>{nc['pan']} · {nc['status']}</span></div>", unsafe_allow_html=True)

    with t4:
        st.markdown("Pre-fill for a client or a whole family. The investor always approves on **their own** device.")
        fam = st.data_editor(pd.DataFrame([{"PAN": "", "Name": "", "Mobile": "", "Email": ""}]), num_rows="dynamic",
                             use_container_width=True, key="fam_editor")
        if st.button("Validate and send consent links", type="primary"):
            existing = {p["contact"]["mobile"] for p in PERSONAS.values()}
            for _, row in fam.iterrows():
                val = lambda x: "" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x).strip()
                pan, mob, em = val(row["PAN"]).upper(), val(row["Mobile"]), val(row["Email"]).lower()
                if not pan:
                    continue
                v = validate_pan(pan)
                if not v["valid"]:
                    st.error(f"{pan}: {v['error']}"); continue
                if mob in (ADVISOR["mobile"], "+91" + ADVISOR["mobile"]) or em == ADVISOR["email"]:
                    st.error(f"🔒 {pan}: contact lock. That's your own mobile/email; clients must use their own.")
                    log(f"Contact lock blocked onboarding of {pan}", "Advisor"); continue
                if mob in existing:
                    st.warning(f"{pan}: this mobile is already used by another client. Allowed, but flagged (+30 risk) for maker-checker review.")
                ss.new_clients.append({"pan": pan, "name": row["Name"] or "New client", "status": "Awaiting investor consent"})
                st.success(f"{pan} ({v['holder_label']}): consent link sent to the investor's phone.")
                log(f"Consent link sent for {pan}", "Advisor")
        for i, nc in enumerate(ss.new_clients):
            if nc["status"] == "Awaiting investor consent":
                if st.button(f"Simulate: {nc['name']} approves via OTP", key=f"appr_{i}"):
                    nc["status"] = "Consent given, journey started"; log(f"Investor consent received for {nc['pan']}", "Investor"); st.rerun()
        st.caption(f"Try the contact lock: enter the advisor's own mobile **{ADVISOR['mobile']}** for a client.")


# ================================================================== ENGINE
def page_engine():
    st.title("Engine inspector")
    st.caption("What the engine sees for the active investor. Every decision is a rule you can audit; AI only assists.")
    options = {f"{p['name'].title()} · {pan}": pan for pan, p in PERSONAS.items()}
    default = list(options.values()).index(ss.cur) if ss.cur in options.values() else 0
    pick = st.selectbox("Investor", list(options.keys()), index=default)
    pan = options[pick]
    if pan != ss.cur:
        open_pan(pan, ss.step if ss.cur == pan else 0)
    p = profile()

    st.subheader("8-stage pipeline")
    cols = st.columns(8)
    for c, (name, status, detail) in zip(cols, rules.stages(p)):
        c.markdown(f"<div class='card' style='min-height:150px'><b>{name}</b><br>{pill(status.upper(), status)}"
                   f"<br><span class='muted'>{detail}</span></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Risk scoring (what-if)")
        w1, w2 = st.columns(2)
        p["pep"] = w1.toggle("PEP", p["pep"])
        p["sanctions_hit"] = w2.toggle("Sanctions list match", p["sanctions_hit"])
        p["high_risk_country"] = w1.toggle("FATF high-risk country", p["high_risk_country"])
        shared = w2.toggle("Mobile shared with other clients", bool(p["shared_contact_with"]))
        p["shared_contact_with"] = ["BCDPK1122M"] if shared else []
        rk = rules.risk(p)
        st.markdown(f"Band {pill(rk['band'], {'Low': 'ok', 'Medium': 'warn', 'High': 'fail'}[rk['band']])} score **{rk['score']}** → route: **{rk['route']}**",
                    unsafe_allow_html=True)
        if rk["factors"]:
            st.dataframe(pd.DataFrame(rk["factors"], columns=["Factor", "Points"]), hide_index=True, use_container_width=True)
        st.caption("Bands: <25 Low · 25–49 Medium · ≥50 High. Weights are illustrative.")
        if p.get("entity") and p["entity"].get("owners"):
            st.subheader("Owner tree → beneficial owners")
            st.dataframe(pd.DataFrame(rules.owner_tree_people(p["entity"]["owners"])).assign(
                via=lambda d: d["via"].map(lambda v: " + ".join(v))), hide_index=True, use_container_width=True)
    with c2:
        st.subheader("Name-matching playground")
        a = st.text_input("Name on PAN", "RAMESH K IYER")
        b = st.text_input("Name on other document", "R K IYER")
        sc = name_score(a, b)
        act = match_action(sc, "that document")
        st.markdown(pill(f"{sc:.2f}", act["level"]) + f" {act['action']}", unsafe_allow_html=True)
        st.caption("Handles initials, word order, titles and Pvt/Ltd abbreviations. ≥0.90 accept · 0.75–0.89 self-declaration · <0.75 fix at source.")
        st.subheader("Audit trail (this session)")
        if ss.log:
            st.dataframe(pd.DataFrame(ss.log[:40]), hide_index=True, use_container_width=True)
        else:
            st.caption("Actions you take in the journey and workspace appear here.")


{"Overview": page_overview, "Investor journey": page_journey,
 "Advisor workspace": page_advisor, "Engine inspector": page_engine}[ss.nav]()
