"""IFANOW · Investor onboarding prototype.

A simple, app-style onboarding flow (one screen per step), built to show the
KYC design from the IFANOW assignment:
  • PAN-first: if KYC already exists, the document steps are skipped
  • DigiLocker for Aadhaar, with a fallback when the Aadhaar mobile doesn't work
  • Names checked across PAN, Aadhaar and bank before anything is submitted
  • PMS is an optional unlock, not a hurdle for every investor
All data is fictional and every external check is simulated.
"""
import time

import streamlit as st

from engine.data import PERSONAS, load_persona
from engine.matching import match_action, name_score
from engine.pan import validate_pan

st.set_page_config(page_title="IFANOW · Open your account", page_icon="🟢", layout="centered",
                   initial_sidebar_state="collapsed")

OTP = "123456"
G, NAVY = "#02B875", "#111D3A"

st.markdown(f"""
<style>
  [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], header, footer {{display:none !important;}}
  .block-container {{max-width: 460px; padding-top: 1.2rem; padding-bottom: 3rem;}}
  .stButton button {{min-height: 48px; border-radius: 12px; font-weight: 600; font-size: 1rem;}}
  .brand {{font-size: 1.15rem; font-weight: 800; color: {NAVY}; letter-spacing: .5px}}
  .brand span {{color: {G}}}
  .h1 {{font-size: 1.6rem; font-weight: 800; color: {NAVY}; line-height: 1.25; margin: .4rem 0 .2rem}}
  .sub {{color: #5d6470; font-size: .95rem; margin-bottom: 1rem}}
  .card {{border: 1px solid #DDE5E1; border-radius: 14px; padding: 14px 16px; margin: 8px 0 14px; background: #fff}}
  .good {{border-color: {G}; background: #F2FBF7}}
  .warn {{border-color: #E9A91F; background: #FFF8E6}}
  .bad  {{border-color: #E8594A; background: #FDEEEC}}
  .tick {{color: {G}; font-weight: 800}}
  .small {{color: #7a808a; font-size: .8rem}}
  .row {{display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid #EEF2F0; font-size:.95rem}}
  .row:last-child {{border-bottom:none}}
</style>""", unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("screen", "welcome")
ss.setdefault("d", {})
d = ss.d


# ------------------------------------------------------------------ flow
def route():
    """The list of screens for this investor. Existing KYC skips the document steps."""
    r = ["welcome", "mobile", "email", "pan"]
    if d.get("entity"):
        r.append("entity")
    if not d.get("kyc_reuse"):
        r += ["aadhaar", "selfie"]
    r += ["details"]
    if not d.get("entity"):
        r.append("nominee")
    r += ["bank", "pms", "review", "done"]
    return r


def go_next():
    r = route()
    ss.screen = r[min(r.index(ss.screen) + 1, len(r) - 1)]


def go_back():
    r = route()
    ss.screen = r[max(r.index(ss.screen) - 1, 0)]


def header(title, sub=None):
    r = route()
    steps = [s for s in r if s not in ("welcome", "done")]
    c1, c2 = st.columns([1, 3])
    if ss.screen not in ("welcome", "done"):
        c1.button("← Back", on_click=go_back, key=f"back_{ss.screen}", type="tertiary")
        n = steps.index(ss.screen) + 1
        c2.markdown(f"<div class='small' style='text-align:right;padding-top:12px'>Step {n} of {len(steps)}</div>", unsafe_allow_html=True)
        st.progress(n / len(steps))
    st.markdown(f"<div class='h1'>{title}</div>", unsafe_allow_html=True)
    if sub:
        st.markdown(f"<div class='sub'>{sub}</div>", unsafe_allow_html=True)


def card(html, kind=""):
    st.markdown(f"<div class='card {kind}'>{html}</div>", unsafe_allow_html=True)


def otp_box(key, label):
    code = st.text_input(label, max_chars=6, key=key, placeholder="Enter 6-digit OTP")
    st.caption(f"Demo OTP: {OTP}")
    return code


# ------------------------------------------------------------------ screens
def welcome():
    st.markdown("<div class='brand'>IFA<span>NOW</span></div>", unsafe_allow_html=True)
    header("Open your investment account", "Takes about 5 minutes. One KYC for mutual funds today, and PMS whenever you're ready.")
    card("<b>Keep these handy</b><br>📱 Mobile number linked to Aadhaar<br>🪪 PAN card<br>🏦 Bank account details")
    st.button("Get started", type="primary", on_click=go_next, width="stretch")
    st.markdown("<div class='small' style='text-align:center;margin-top:18px'>Prototype · demo data only · no real checks are made</div>",
                unsafe_allow_html=True)


def mobile():
    header("What's your mobile number?", "We'll send a one-time password to verify it.")
    num = st.text_input("Mobile number", value=d.get("mobile", ""), max_chars=10, placeholder="10-digit mobile")
    if not d.get("mobile_sent"):
        if st.button("Send OTP", type="primary", width="stretch"):
            if len(num) == 10 and num.isdigit():
                d["mobile"], d["mobile_sent"] = num, True
                st.rerun()
            else:
                st.error("Please enter a valid 10-digit mobile number.")
    else:
        code = otp_box("otp_m", f"OTP sent to +91 {d['mobile']}")
        if st.button("Verify", type="primary", width="stretch"):
            if code == OTP:
                go_next(); st.rerun()
            else:
                st.error("That OTP doesn't match. Try 123456.")


def email():
    header("Your email address", "For statements and important updates.")
    em = st.text_input("Email", value=d.get("email", ""), placeholder="name@example.com")
    if not d.get("email_sent"):
        if st.button("Send OTP", type="primary", width="stretch"):
            if "@" in em and "." in em.split("@")[-1]:
                d["email"], d["email_sent"] = em, True
                st.rerun()
            else:
                st.error("Please enter a valid email.")
    else:
        code = otp_box("otp_e", f"OTP sent to {d['email']}")
        if st.button("Verify", type="primary", width="stretch"):
            if code == OTP:
                go_next(); st.rerun()
            else:
                st.error("That OTP doesn't match. Try 123456.")


def pan():
    header("Enter your PAN", "We'll check if your KYC already exists, so you don't have to repeat it.")
    p = st.text_input("PAN", value=d.get("pan", ""), max_chars=10, placeholder="ABCDE1234F").strip().upper()
    with st.expander("Demo PANs to try"):
        st.markdown("• **ABCPS1234K**: KYC already done (short journey)  \n"
                    "• **AKIPI9753R**: name spelled differently on documents  \n"
                    "• **AFRPR5678L**: Aadhaar mobile no longer works  \n"
                    "• **AKNPM4321Q**: NRI living in the US  \n"
                    "• **AADCA1357P**: a company PAN  \n"
                    "• Any other PAN: a brand-new investor")
    if st.button("Check PAN", type="primary", width="stretch"):
        v = validate_pan(p)
        if not v["valid"]:
            st.error(v["error"]); return
        prof = load_persona(p)
        known = p in PERSONAS
        d.update({"pan": p, "holder": v["holder_label"], "entity": v["segment"] != "individual",
                  "name": prof["name"] if known else "", "kra": prof["kra"]["status"],
                  "aadhaar_name": prof["aadhaar"]["name"] if known else "",
                  "aadhaar_mobile_ok": prof["aadhaar"]["mobile_active"],
                  "bank_name": prof["bank"]["holder_name"] if known else "",
                  "demat_name": (prof["demat"] or {}).get("holder_name", "") if known else "",
                  "nri": prof["residency"] == "nri", "us": prof["us_person"], "persona": prof,
                  "pan_checked": True})
        d["kyc_reuse"] = d["kra"] == "Validated"
        st.rerun()
    if d.get("pan_checked") and d.get("pan") == p:
        kra = d["kra"]
        if not d["name"]:
            d["name"] = st.text_input("Full name as on PAN", placeholder="As printed on your PAN").strip().upper()
        else:
            st.markdown(f"**Name on PAN:** {d['name']}")
        if d["entity"]:
            card(f"This PAN belongs to a <b>{d['holder']}</b>. We'll ask for a few entity documents next.", "warn")
        if kra == "Validated":
            card("<span class='tick'>✓</span> <b>Good news! Your KYC is already verified.</b><br>"
                 "We'll reuse it, so you can skip the Aadhaar and selfie steps.", "good")
        elif kra == "Registered":
            card("<b>Your KYC needs a quick refresh.</b><br>It was done with an older document. A 1-minute Aadhaar check "
                 "lets you invest with every fund house.", "warn")
        elif kra == "On Hold":
            card("<b>Your KYC is on hold</b> (" + d["persona"]["kra"]["reason"].lower() + ").<br>"
                 "We'll fix it right here. You won't need to visit anyone.", "bad")
        else:
            card("<b>Let's set up your KYC.</b> It takes about 3 minutes with DigiLocker, with no paper forms.")
        if d["us"]:
            card("🇺🇸 You're a US tax resident. Some fund houses don't accept US investors, so we'll <b>only show you the ones that do</b>.", "warn")
        if st.button("Continue", type="primary", disabled=not d["name"], width="stretch"):
            go_next(); st.rerun()


def entity():
    header(f"{d['holder']} documents", "A few extra documents for non-individual accounts.")
    docs = {
        "Hindu Undivided Family (HUF)": ["HUF declaration / deed", "Karta's PAN", "HUF bank proof", "List of coparceners"],
        "Company": ["Certificate of Incorporation", "MoA / AoA", "Board resolution to invest", "List of owners above 10%"],
    }.get(d["holder"], ["Registration certificate / deed", "Authorised signatory list", "Owners above 10%"])
    done = [st.checkbox(f"{x}  (uploaded)", key=f"doc_{x}") for x in docs]
    if d["holder"] == "Company":
        card("<b>Who ultimately owns the company?</b><br>Kavita Desai: 62.5% (40% directly + via Desai Holdings LLP)<br>"
             "Sunil Desai: 22.5% (via Desai Holdings LLP)<br><span class='small'>Everyone above 10% completes a quick KYC by link.</span>")
    st.caption("Next, the authorised signatory verifies with DigiLocker.")
    if st.button("Continue", type="primary", disabled=not all(done), width="stretch"):
        go_next(); st.rerun()


def aadhaar():
    header("Verify with DigiLocker", "Your Aadhaar and PAN are shared securely from DigiLocker. Nothing to upload.")
    if not d.get("aadhaar_ok"):
        if st.button("Continue with DigiLocker", type="primary", width="stretch"):
            with st.spinner("Connecting to DigiLocker…"):
                time.sleep(1.2)
            if d.get("aadhaar_mobile_ok", True):
                d["aadhaar_ok"] = True
                d["aadhaar_name"] = d.get("aadhaar_name") or d["name"]
            else:
                d["dl_failed"] = True
            st.rerun()
        if d.get("dl_failed"):
            card("<b>We couldn't send the OTP.</b><br>The mobile number linked to your Aadhaar seems inactive. "
                 "No problem, choose another way:", "bad")
        with st.expander("Aadhaar-linked mobile not working?", expanded=bool(d.get("dl_failed"))):
            if st.button("Upload offline Aadhaar file (XML)", width="stretch"):
                d["aadhaar_ok"], d["aadhaar_name"] = True, d.get("aadhaar_name") or d["name"]; st.rerun()
            if st.button("Quick video call with an expert (2 min)", width="stretch"):
                d["aadhaar_ok"], d["aadhaar_name"] = True, d.get("aadhaar_name") or d["name"]; st.rerun()
        return
    card(f"<span class='tick'>✓</span> <b>Aadhaar verified</b><br>Name: {d['aadhaar_name']}<br>Aadhaar: XXXX XXXX 4821", "good")
    ok = name_check("Aadhaar", d["aadhaar_name"])
    if st.button("Continue", type="primary", disabled=not ok, width="stretch"):
        go_next(); st.rerun()


def name_check(source, other):
    """Returns True if the investor may continue."""
    sc = name_score(d["name"], other)
    act = match_action(sc, source)
    if act["level"] == "ok":
        if sc < 1:
            st.caption(f"Name on {source} ({other}) matches your PAN ({d['name']}).")
        return True
    if act["level"] == "warn":
        card(f"<b>Small name difference</b><br>PAN: {d['name']}<br>{source}: {other}<br>"
             "<span class='small'>This is common. Just confirm it's you, and we'll attach a declaration so nothing gets rejected later.</span>", "warn")
        return st.checkbox(f"Yes, both names belong to me", key=f"decl_{source}")
    card(f"<b>Name doesn't match</b><br>PAN: {d['name']}<br>{source}: {other}", "bad")
    return False


def selfie():
    header("Take a quick selfie", "This confirms it's really you and matches your Aadhaar photo.")
    pic = st.camera_input("Look at the camera", label_visibility="collapsed")
    use_sample = st.button("No camera? Use a sample photo (demo)", width="stretch")
    if pic or use_sample or d.get("selfie_ok"):
        if not d.get("selfie_ok"):
            with st.spinner("Checking…"):
                time.sleep(1)
            d["selfie_ok"] = True
        card("<span class='tick'>✓</span> <b>Live photo confirmed</b> · matches your Aadhaar photo", "good")
        if st.button("Continue", type="primary", width="stretch"):
            go_next(); st.rerun()


def details():
    header("A few details about you", "Required by SEBI for every investor.")
    d["occupation"] = st.selectbox("Occupation", ["Salaried", "Self-employed / Business", "Professional", "Retired", "Student", "Homemaker"])
    d["income"] = st.selectbox("Annual income", ["Below ₹5 lakh", "₹5–10 lakh", "₹10–25 lakh", "₹25 lakh – ₹1 crore", "Above ₹1 crore"])
    status = st.radio("Residential status", ["Resident Indian", "NRI", "OCI"], horizontal=True, index=1 if d.get("nri") else 0)
    d["nri"] = status != "Resident Indian"
    tax = st.radio("Do you pay tax in any country other than India?", ["No", "Yes"], horizontal=True, index=1 if d.get("us") else 0)
    if tax == "Yes":
        c1, c2 = st.columns(2)
        country = c1.selectbox("Country", ["United States", "United Kingdom", "UAE", "Singapore", "Canada", "Other"])
        c2.text_input("Tax ID in that country")
        d["us"] = country in ("United States", "Canada")
    pep = st.radio("Are you or a close family member a politician or senior government official?", ["No", "Yes"], horizontal=True)
    if pep == "Yes":
        st.caption("Thanks for telling us. Our team will do a quick additional review; you can continue.")
    if st.button("Continue", type="primary", width="stretch"):
        go_next(); st.rerun()


def nominee():
    header("Add a nominee", "Who should receive your investments if something happens to you?")
    n = st.text_input("Nominee's full name")
    c1, c2 = st.columns(2)
    c1.selectbox("Relationship", ["Spouse", "Child", "Parent", "Sibling", "Other"])
    c2.date_input("Nominee's date of birth", value=None, format="DD/MM/YYYY")
    if st.button("Save nominee", type="primary", disabled=not n, width="stretch"):
        d["nominee"] = n; go_next(); st.rerun()
    if st.button("Skip, I don't want to add a nominee", width="stretch"):
        d["nominee"] = "Opted out"; go_next(); st.rerun()


def bank():
    header("Link your bank account", "Investments are paid from and returned to this account.")
    acc = st.text_input("Account number", type="password")
    acc2 = st.text_input("Re-enter account number")
    ifsc = st.text_input("IFSC", max_chars=11, placeholder="e.g. HDFC0001234").upper()
    types = ["NRE", "NRO"] if d.get("nri") else ["Savings", "Current"]
    kind = st.radio("Account type", types, horizontal=True)
    if d.get("nri"):
        st.caption("As an NRI you can invest from an NRE or NRO account only.")
    if not d.get("bank_ok"):
        if st.button("Verify account", type="primary", width="stretch"):
            if not acc or acc != acc2:
                st.error("Account numbers don't match."); return
            if len(ifsc) != 11:
                st.error("IFSC should be 11 characters."); return
            with st.spinner("Sending ₹1 to your account to verify it…"):
                time.sleep(1.2)
            d["bank_ok"], d["bank_type"] = True, kind
            d["bank_name"] = d.get("bank_name") or d["name"]
            st.rerun()
        return
    card(f"<span class='tick'>✓</span> <b>₹1 received</b> · account holder: {d['bank_name']}", "good")
    ok = name_check("Bank", d["bank_name"])
    if st.button("Continue", type="primary", disabled=not ok, width="stretch"):
        go_next(); st.rerun()


def pms():
    header("Planning to invest ₹50 lakh or more?", "Portfolio Management Services (PMS) need a couple of extra steps. You can do them now or anytime later.")
    card("✅ <b>Mutual funds:</b> you're all set after the next step.<br>➕ <b>PMS:</b> link your demat account and confirm your source of funds.")
    if d.get("pms") is None:
        c1, c2 = st.columns(2)
        if c1.button("Maybe later", width="stretch"):
            d["pms"] = "later"; go_next(); st.rerun()
        if c2.button("Set up PMS", type="primary", width="stretch"):
            d["pms"] = "setting"; st.rerun()
        return
    if d["pms"] == "setting":
        if not d.get("demat_ok"):
            if st.button("Link demat account (CDSL / NSDL)", type="primary", width="stretch"):
                with st.spinner("Fetching your demat details…"):
                    time.sleep(1)
                d["demat_ok"] = True; d["demat_name"] = d.get("demat_name") or d["name"]; st.rerun()
            return
        card(f"<span class='tick'>✓</span> <b>Demat linked</b> · holder: {d['demat_name']}", "good")
        sc = name_score(d["name"], d["demat_name"])
        if match_action(sc, "Demat")["level"] == "fail":
            card("<b>PMS paused, but mutual funds are not affected.</b><br>The name on your demat account ("
                 f"{d['demat_name']}) differs from your PAN. Ask your broker/DP to update it; we'll notify you when it's done.", "warn")
            if st.button("Continue with mutual funds", type="primary", width="stretch"):
                d["pms"] = "paused"; go_next(); st.rerun()
            return
        if not d.get("aa_ok"):
            st.markdown("**Confirm your source of funds**")
            st.caption("Instead of uploading bank statements, approve a one-time, secure share from your bank (RBI Account Aggregator).")
            if st.button("Approve via Account Aggregator", type="primary", width="stretch"):
                with st.spinner("Waiting for your bank…"):
                    time.sleep(1.2)
                d["aa_ok"] = True; st.rerun()
            return
        card("<span class='tick'>✓</span> <b>Source of funds confirmed</b> via Account Aggregator", "good")
        if st.button("Continue", type="primary", width="stretch"):
            d["pms"] = "ready"; go_next(); st.rerun()


def review():
    header("Review and sign", "One Aadhaar OTP signs everything.")
    rows = [("Name", d.get("name")), ("PAN", d.get("pan")), ("Mobile", "+91 " + d.get("mobile", "")), ("Email", d.get("email")),
            ("KYC", "Reused (already verified)" if d.get("kyc_reuse") else "Verified via DigiLocker"),
            ("Bank", f"{d.get('bank_type', '')} · {d.get('bank_name', '')}")]
    if not d.get("entity"):
        rows.append(("Nominee", d.get("nominee", "-")))
    rows.append(("PMS", {"ready": "Set up", "paused": "Paused (demat name)", "later": "Later"}.get(d.get("pms"), "Later")))
    card("".join(f"<div class='row'><span class='small'>{k}</span><span>{v}</span></div>" for k, v in rows))
    agree = st.checkbox("I agree to the terms and confirm these details are correct")
    if not d.get("esign_sent"):
        if st.button("eSign with Aadhaar OTP", type="primary", disabled=not agree, width="stretch"):
            d["esign_sent"] = True; st.rerun()
    else:
        code = otp_box("otp_s", "OTP sent to your Aadhaar-linked mobile")
        if st.button("Sign", type="primary", width="stretch"):
            if code == OTP:
                go_next(); st.rerun()
            else:
                st.error("That OTP doesn't match. Try 123456.")


def done():
    st.markdown("<div style='text-align:center;font-size:3rem;margin-top:1rem'>🎉</div>", unsafe_allow_html=True)
    first = (d.get("name") or "there").split()[0].title()
    st.markdown(f"<div class='h1' style='text-align:center'>You're all set, {first}!</div>", unsafe_allow_html=True)
    st.markdown("<div class='sub' style='text-align:center'>Here's what you can invest in right now.</div>", unsafe_allow_html=True)
    pms_line = {"ready": "<span class='tick'>✓ Ready</span>",
                "paused": "⏸ Paused until your demat name is updated",
                }.get(d.get("pms"), "➕ Available anytime · 2 quick steps")
    mf_line = "<span class='tick'>✓ Ready</span>" + (" · US-friendly fund houses only" if d.get("us") else "")
    card(f"<div class='row'><b>Mutual funds</b><span>{mf_line}</span></div>"
         f"<div class='row'><b>PMS (₹50L+)</b><span>{pms_line}</span></div>"
         "<div class='row'><b>Bonds, AIFs</b><span class='small'>Coming soon, same KYC</span></div>", "good")
    st.caption("Your KYC is registered with the KRA and the central KYC registry (CKYC), so you won't need to repeat it with any other SEBI-registered platform.")
    if st.button("Start over (demo)", type="primary", width="stretch"):
        ss.clear(); st.rerun()


SCREENS = {"welcome": welcome, "mobile": mobile, "email": email, "pan": pan, "entity": entity, "aadhaar": aadhaar,
           "selfie": selfie, "details": details, "nominee": nominee, "bank": bank, "pms": pms, "review": review, "done": done}
SCREENS[ss.screen]()
