"""Deterministic rules: readiness per asset, risk scoring, routing and the
8-stage engine view. "AI assists, rules decide": every approve / block below
is a plain rule that can be audited.
"""
from .matching import reconcile

ENTITY_SEGMENTS = {"huf", "corporate", "partnership", "trust", "other_entity"}
CASH_INTENSIVE = {"Business owner", "Jeweller", "Real estate"}
PMS_MIN_LAKH = 50


def is_entity(p):
    return p.get("segment") in ENTITY_SEGMENTS


def is_hni(p):
    return p["income_lakh"] >= 50 or p["planned_pms_lakh"] >= PMS_MIN_LAKH or p["advisor_tag_pms"]


def needs_segment_pack(p):
    return p["residency"] == "nri" or is_entity(p) or is_hni(p)


def name_checks(p):
    others = {}
    if not is_entity(p) and p["aadhaar"]["name"]:
        others["Aadhaar"] = p["aadhaar"]["name"]
    if p["bank"]["verified"]:
        others["Bank"] = p["bank"]["holder_name"]
    if p["demat"] and p["demat"]["linked"]:
        others["Demat"] = p["demat"]["holder_name"]
    rows = reconcile(p["name"], others)
    for r in rows:
        r["resolved"] = r["level"] == "ok" or (r["level"] == "warn" and r["source"] in p.get("declarations", set()))
    return rows


def _name_ok(p, source):
    for r in name_checks(p):
        if r["source"] == source:
            return r["resolved"]
    return True


def core_gaps(p):
    g = []
    if not is_entity(p) and not p["itd"]["pan_aadhaar_linked"]:
        g.append(("Link PAN with Aadhaar", "KRA cannot validate KYC until PAN and Aadhaar are linked"))
    if not is_entity(p) and not (p["aadhaar"]["verified"] or p["aadhaar"]["xml_fallback"]):
        g.append(("Verify identity (DigiLocker / Aadhaar XML / VIPV)", "Identity must be verified at source"))
    if not is_entity(p) and not p["liveness"]:
        g.append(("Selfie liveness + face match", "Confirms a live person matching the ID photo"))
    if not p["contact"]["mobile_verified"]:
        g.append(("Verify mobile by OTP", "Unverified contact details put KYC On Hold"))
    if p["contact"]["email"] and not p["contact"]["email_verified"]:
        g.append(("Verify email by OTP", "Unverified contact details put KYC On Hold"))
    if needs_segment_pack(p) and not p["segment_pack_done"]:
        g.append(("Complete segment pack", "Extra details for this investor type"))
    if not _name_ok(p, "Aadhaar"):
        g.append(("Resolve Aadhaar name mismatch", "Name differs from PAN"))
    return g


def kra_effective(p):
    """KRA status after the journey: completing the core re-validates / creates the record."""
    st = p["kra"]["status"]
    if st == "Validated":
        return st
    return "Validated (on completion)" if not core_gaps(p) else st


def mf_gaps(p):
    g = list(core_gaps(p))
    if not p["fatca_done"]:
        g.append(("FATCA / CRS self-certification", "Mandatory tax-residency declaration"))
    if not is_entity(p) and not p["nominee_done"]:
        g.append(("Add nominee or opt out", "Required for individual folios"))
    if not p["bank"]["verified"]:
        g.append(("Verify bank (penny drop)", "Confirms the account belongs to the investor"))
    elif not _name_ok(p, "Bank"):
        g.append(("Resolve bank name mismatch", "Bank account name differs from PAN"))
    if p["residency"] == "nri" and not any(t in p["bank"]["account_type"] for t in ("NRE", "NRO")):
        g.append(("Use an NRE / NRO account", "NRIs cannot invest from a resident savings account"))
    if not p["ucc_created"]:
        g.append(("Create UCC (BSE/NSE) or MFU CAN", "Client ID needed on the transaction platform"))
    return g


def pms_gaps(p):
    g = [x for x in mf_gaps(p) if not x[0].startswith("Add nominee")]
    d = p["demat"]
    if not d or not d["linked"]:
        g.append(("Link demat account", "PMS holds securities in the investor's own demat"))
    else:
        if not _name_ok(p, "Demat"):
            g.append(("Fix demat name at DP", "Demat name differs from PAN; blocks PMS only"))
        if not d["ddpi"]:
            g.append(("Sign DDPI", "Lets the portfolio manager operate the demat"))
    if not p["source_of_funds_verified"]:
        g.append(("Source of funds via Account Aggregator", "₹50L+ must be explainable"))
    if p["planned_pms_lakh"] < PMS_MIN_LAKH:
        g.append((f"Commit at least ₹{PMS_MIN_LAKH}L", "SEBI minimum per PMS client"))
    if not p["suitability_done"]:
        g.append(("Suitability questionnaire", "PMS must fit the investor's risk profile"))
    if not p["pms_agreement_signed"]:
        g.append(("eSign PMS agreement + MITC + fee acknowledgement", "Required before the PMS firm activates"))
    return g


def us_amc_note(p):
    if p["us_person"]:
        return "US person under FATCA: only fund houses that accept US/Canada investors are shown (demo list: 6 of 40+ AMCs)."
    return None


# ------------------------------------------------------------------ risk
def risk(p):
    f = []
    if p["sanctions_hit"]:
        return {"score": 100, "band": "High", "factors": [("Sanctions list match", 100)], "route": "Blocked · report to compliance (STR review)"}
    if p["pep"]:
        f.append(("Politically Exposed Person", 40))
    if p["high_risk_country"]:
        f.append(("FATF high-risk jurisdiction", 30))
    if p["residency"] == "nri":
        f.append(("Non-resident", 10))
    if p["us_person"]:
        f.append(("US person (FATCA reporting)", 5))
    ent = p.get("entity") or {}
    if any(o.get("kind") == "entity" for o in ent.get("owners", [])):
        f.append(("Layered ownership", 15))
    if p["occupation"] in CASH_INTENSIVE:
        f.append(("Cash-intensive occupation", 10))
    if p["planned_pms_lakh"] > 3 * max(p["income_lakh"], 1):
        f.append(("Ticket > 3× declared income", 5 if p["source_of_funds_verified"] else 25))
    if p["shared_contact_with"]:
        f.append(("Contact shared with other clients", 30))
    if p["kra"]["status"] == "On Hold":
        f.append(("Existing KYC On Hold (data quality)", 10))
    s = sum(x[1] for x in f)
    band = "Low" if s < 25 else ("Medium" if s < 50 else "High")
    route = {"Low": "Auto-approve", "Medium": "Compliance maker-checker review",
             "High": "Enhanced due diligence + senior approval"}[band]
    return {"score": s, "band": band, "factors": f, "route": route}


# ------------------------------------------------------------------ owner tree
def _walk(owners, parent_pct, path):
    out = []
    for o in owners:
        eff = parent_pct * o["pct"] / 100
        label = f"{path} → {o['name']}" if path else o["name"]
        if o.get("kind") == "entity":
            out += _walk(o.get("owners", []), eff, label)
        elif o.get("kind") == "person":
            out.append({"person": o["name"], "pct": eff, "via": label, "kyc": o["kyc"]})
    return out


def owner_tree_people(owners):
    """Flatten an ownership tree to natural persons with their effective %."""
    merged = {}
    for r in _walk(owners, 100.0, ""):
        m = merged.setdefault(r["person"], {"person": r["person"], "effective_pct": 0.0, "via": [], "kyc": True})
        m["effective_pct"] = round(m["effective_pct"] + r["pct"], 1)
        m["via"].append(r["via"])
        m["kyc"] = m["kyc"] and r["kyc"]
    return list(merged.values())


# ------------------------------------------------------------------ 8 stages
def stages(p):
    rk = risk(p)
    nm = name_checks(p)
    worst = "ok"
    for r in nm:
        if not r["resolved"]:
            worst = "fail" if r["level"] == "fail" else ("warn" if worst != "fail" else worst)
    core = core_gaps(p)
    def s(ok, warn=False):
        return "ok" if ok else ("warn" if warn else "pending")
    ident = is_entity(p) or p["aadhaar"]["verified"] or p["aadhaar"]["xml_fallback"]
    return [
        ("1 · Capture", s(ident), "DigiLocker pull" if p["aadhaar"]["verified"] else ("Aadhaar XML fallback" if p["aadhaar"]["xml_fallback"] else "Awaiting documents")),
        ("2 · Validate", s(p["contact"]["mobile_verified"]), "PAN format ✓ · holder type from PAN ✓ · OTP " + ("✓" if p["contact"]["mobile_verified"] else "pending")),
        ("3 · Verify", s(is_entity(p) or p["itd"]["pan_aadhaar_linked"], warn=True), f"ITD PAN–Aadhaar link: {'✓' if p['itd']['pan_aadhaar_linked'] else '✗'} · KRA: {p['kra']['status']} · CKYC: {'found' if p['ckyc']['found'] else 'none'}"),
        ("4 · Reconcile", worst if nm else "pending", f"{len(nm)} name source(s) compared" if nm else "No second source yet"),
        ("5 · Screen", "fail" if p["sanctions_hit"] else ("warn" if p["pep"] else "ok"), "PEP " + ("hit" if p["pep"] else "clear") + " · UN/UAPA " + ("HIT" if p["sanctions_hit"] else "clear") + " · adverse media clear"),
        ("6 · Score", {"Low": "ok", "Medium": "warn", "High": "fail"}[rk["band"]], f"{rk['band']} risk (score {rk['score']})"),
        ("7 · Route", "ok" if not core else "pending", rk["route"] if not core else "Waiting for core KYC"),
        ("8 · Monitor", "ok", "Re-KYC every " + {"Low": "10 years", "Medium": "8 years", "High": "2 years"}[rk["band"]] + " (demo) · On Hold alerts on"),
    ]


# ------------------------------------------------------------------ exception explainer (EN / HI)
EXPLAIN = {
    "on_hold_contact": ("Your KYC is on hold because your mobile/email isn't verified. Tap the link, enter the OTP, and you're done in 2 minutes.",
                        "आपका KYC होल्ड पर है क्योंकि आपका मोबाइल/ईमेल सत्यापित नहीं है। लिंक पर टैप करें, OTP डालें, 2 मिनट में काम हो जाएगा।"),
    "pan_aadhaar": ("Your PAN isn't linked to Aadhaar, so your KYC can't be validated. Link it on the Income Tax portal, then tap 'Recheck'.",
                    "आपका PAN आधार से लिंक नहीं है, इसलिए आपका KYC सत्यापित नहीं हो सकता। आयकर पोर्टल पर इसे लिंक करें, फिर 'दोबारा जाँचें' पर टैप करें।"),
    "registered": ("Your KYC is 'Registered', not 'Validated'. A one-time Aadhaar check lets you invest with any fund house.",
                   "आपका KYC 'Registered' है, 'Validated' नहीं। एक बार आधार से जाँच करने पर आप किसी भी फंड हाउस में निवेश कर पाएँगे।"),
    "passport": ("Your passport on record expires soon. Upload the renewed passport to keep investing without interruption.",
                 "आपके रिकॉर्ड में दर्ज पासपोर्ट जल्द समाप्त हो रहा है। बिना रुकावट निवेश जारी रखने के लिए नया पासपोर्ट अपलोड करें।"),
    "pms_gap": ("You're a few steps from PMS: link your demat and share bank data via Account Aggregator.",
                "PMS के लिए बस कुछ कदम बाकी हैं: अपना डीमैट लिंक करें और अकाउंट एग्रीगेटर से बैंक डेटा साझा करें।"),
    "not_found": ("There's no KYC on record for you yet. It takes about 8 minutes with DigiLocker, with no paper forms.",
                  "आपका KYC अभी रिकॉर्ड में नहीं है। DigiLocker से लगभग 8 मिनट लगेंगे, कोई कागज़ी फ़ॉर्म नहीं।"),
}
