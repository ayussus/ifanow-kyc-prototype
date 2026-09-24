"""Mock registries and demo personas.

Every PAN, name and number here is fictional. The functions below stand in
for real calls to the Income Tax Dept, KRA, CKYC registry, DigiLocker, bank
penny-drop and depositories, and return canned responses per persona.
"""
import copy

ADVISOR = {"name": "Neha Kulkarni", "firm": "Wealth Compass (ARN-000000, demo)",
           "mobile": "9800000001", "email": "neha@wealthcompass.demo"}


def _base(**kw):
    p = {
        "pan": "", "name": "", "dob": "1990-01-01", "residency": "resident", "country": "India",
        "us_person": False, "occupation": "Salaried", "income_lakh": 12, "planned_pms_lakh": 0,
        "advisor_tag_pms": False,
        "kra": {"status": "Validated", "agency": "CVL KRA", "reason": ""},
        "ckyc": {"found": True, "kin": "50000000000001"},
        "itd": {"pan_aadhaar_linked": True},
        "aadhaar": {"name": "", "mobile_active": True, "verified": False, "xml_fallback": False},
        "liveness": False, "face_match": None,
        "contact": {"mobile": "", "email": "", "mobile_verified": False, "email_verified": False},
        "bank": {"holder_name": "", "account_type": "Savings", "verified": False},
        "demat": None,
        "fatca_done": False, "nominee_done": False, "ucc_created": False, "mandate_done": False,
        "source_of_funds_verified": False, "aa_balance_lakh": None, "suitability_done": False,
        "pms_agreement_signed": False, "pms_pack_sent": False,
        "pep": False, "sanctions_hit": False, "high_risk_country": False,
        "segment_pack_done": False, "entity": None,
        "folios": 0, "folio_on_hold": False, "shared_contact_with": [],
        "passport": None, "overseas_address": None,
    }
    for k, v in kw.items():
        p[k] = v
    return p


PERSONAS = {
    "ABCPS1234K": _base(
        pan="ABCPS1234K", name="PRIYA SHARMA", dob="1998-04-12", occupation="Software engineer", income_lakh=14,
        aadhaar={"name": "PRIYA SHARMA", "mobile_active": True, "verified": False, "xml_fallback": False},
        contact={"mobile": "9811111111", "email": "priya@example.com", "mobile_verified": False, "email_verified": False},
        bank={"holder_name": "PRIYA SHARMA", "account_type": "Savings", "verified": False}, folios=2,
        _story="Resident first-timer. Already KRA-validated, so nothing needs uploading: she is MF-ready in minutes."),
    "AFRPR5678L": _base(
        pan="AFRPR5678L", name="VENKATESH RAO", dob="1958-09-02", occupation="Retired", income_lakh=9,
        kra={"status": "On Hold", "agency": "NDML", "reason": "Mobile / email not validated"},
        aadhaar={"name": "VENKATESH RAO", "mobile_active": False, "verified": False, "xml_fallback": False},
        contact={"mobile": "9822222222", "email": "", "mobile_verified": False, "email_verified": False},
        bank={"holder_name": "VENKATESH RAO", "account_type": "Savings (pension)", "verified": False},
        folios=5, folio_on_hold=True,
        _story="Retiree (67). KRA On Hold and his Aadhaar-linked mobile no longer works, so the OTP route fails. The engine offers an Aadhaar XML or advisor-led video KYC fallback."),
    "AKNPM4321Q": _base(
        pan="AKNPM4321Q", name="ARJUN MEHTA", dob="1989-11-20", residency="nri", country="United States",
        us_person=True, occupation="Product manager", income_lakh=90,
        kra={"status": "Registered", "agency": "CAMS KRA", "reason": "Address proof was not Aadhaar"},
        aadhaar={"name": "ARJUN MEHTA", "mobile_active": True, "verified": False, "xml_fallback": False},
        contact={"mobile": "+1 4155550100", "email": "arjun@example.com", "mobile_verified": False, "email_verified": False},
        bank={"holder_name": "ARJUN MEHTA", "account_type": "Savings", "verified": False},
        _story="NRI in the US. KRA 'Registered', and many fund houses refuse US persons under FATCA. The engine flags this at Step 0 and only shows fund houses that accept him."),
    "AMSPS8765D": _base(
        pan="AMSPS8765D", name="MEERA SHAH", dob="1976-02-14", occupation="Business owner", income_lakh=85,
        planned_pms_lakh=75, advisor_tag_pms=True,
        aadhaar={"name": "MEERA SHAH", "mobile_active": True, "verified": False, "xml_fallback": False},
        contact={"mobile": "9833333333", "email": "meera@example.com", "mobile_verified": False, "email_verified": False},
        bank={"holder_name": "MEERA SHAH", "account_type": "Savings", "verified": False},
        demat={"linked": False, "holder_name": "MEERA SHAH", "dp": "CDSL", "ddpi": False}, folios=6,
        _story="HNI moving to PMS. Her advisor tagged PMS interest, so the predictive trigger asks for Tier-2 data early. Source of funds comes via Account Aggregator."),
    "AKIPI9753R": _base(
        pan="AKIPI9753R", name="RAMESH K IYER", dob="1982-07-30", occupation="Doctor", income_lakh=60,
        planned_pms_lakh=55,
        aadhaar={"name": "RAMESH IYER", "mobile_active": True, "verified": False, "xml_fallback": False},
        contact={"mobile": "9844444444", "email": "ramesh@example.com", "mobile_verified": False, "email_verified": False},
        bank={"holder_name": "RAMESH KRISHNAN IYER", "account_type": "Savings", "verified": False},
        demat={"linked": False, "holder_name": "R K IYER", "dp": "NSDL", "ddpi": False},
        _story="Name mismatch demo. PAN, bank, Aadhaar and demat spell his name four ways. The engine scores each one and blocks only the tier that is actually affected."),
    "AAEHS2468F": _base(
        pan="AAEHS2468F", name="SHARMA FAMILY HUF", dob="2004-01-01", occupation="HUF", income_lakh=30,
        kra={"status": "Not found", "agency": "", "reason": "No KYC record for this PAN"},
        ckyc={"found": False, "kin": ""},
        aadhaar={"name": "RAJESH SHARMA", "mobile_active": True, "verified": False, "xml_fallback": False},
        contact={"mobile": "9855555555", "email": "rajesh@example.com", "mobile_verified": False, "email_verified": False},
        bank={"holder_name": "SHARMA FAMILY HUF", "account_type": "Current (HUF)", "verified": False},
        entity={"type": "huf", "karta": "RAJESH SHARMA", "docs": {"HUF PAN": True, "HUF deed / declaration": False, "HUF bank proof": True},
                "members": [{"name": "RAJESH SHARMA", "role": "Karta", "kyc": True},
                            {"name": "ANITA SHARMA", "role": "Coparcener", "kyc": True},
                            {"name": "ROHAN SHARMA", "role": "Coparcener (minor, guardian: Karta)", "kyc": False}]},
        _story="HUF. PAN 4th char 'H' routes to the HUF pack: Karta KYC, coparcener list and an HUF bank account."),
    "AADCA1357P": _base(
        pan="AADCA1357P", name="ACME TEXTILES PRIVATE LIMITED", dob="2011-06-01", occupation="Company", income_lakh=400,
        planned_pms_lakh=200,
        kra={"status": "Validated", "agency": "CVL KRA", "reason": ""},
        aadhaar={"name": "", "mobile_active": True, "verified": True, "xml_fallback": False},
        contact={"mobile": "9866666666", "email": "finance@acme.demo", "mobile_verified": False, "email_verified": False},
        bank={"holder_name": "ACME TEXTILES PVT LTD", "account_type": "Current", "verified": False},
        demat={"linked": False, "holder_name": "ACME TEXTILES PRIVATE LIMITED", "dp": "CDSL", "ddpi": False},
        entity={"type": "corporate", "docs": {"Certificate of Incorporation": True, "MoA / AoA": True, "Board resolution for investment": False},
                "owners": [
                    {"name": "KAVITA DESAI", "pct": 40, "kind": "person", "kyc": True},
                    {"name": "DESAI HOLDINGS LLP", "pct": 45, "kind": "entity", "kyc": True, "owners": [
                        {"name": "KAVITA DESAI", "pct": 50, "kind": "person", "kyc": True},
                        {"name": "SUNIL DESAI", "pct": 50, "kind": "person", "kyc": False}]},
                    {"name": "12 minority shareholders", "pct": 15, "kind": "group", "kyc": None}]},
        _story="Corporate with layered ownership. The owner-tree builder traces through the holding LLP to find every person with more than 10%."),
}

CLIENT_BOOK_EXTRA = [
    {"pan": "BCDPK1122M", "name": "KIRAN PATIL", "kra": "Validated", "mf_ready": True, "pms_gap": [], "issue": None},
    {"pan": "BDKPJ3344N", "name": "JOSEPH D'SOUZA", "kra": "Registered", "mf_ready": False, "pms_gap": [],
     "issue": "KRA Registered: needs Aadhaar re-validation before investing with a new fund house"},
    {"pan": "BEMPN5566P", "name": "NAZIA KHAN", "kra": "On Hold", "mf_ready": False, "pms_gap": [],
     "issue": "KRA On Hold: PAN not linked to Aadhaar. All transactions blocked"},
    {"pan": "BFLPS7788Q", "name": "SURESH MENON", "kra": "Validated", "mf_ready": True, "pms_gap": [],
     "issue": "Passport expires in 45 days (NRI): re-verify before next order"},
    {"pan": "BGNPT9900R", "name": "TANVI GUPTA", "kra": "Validated", "mf_ready": True, "pms_gap": [], "issue": None},
]


def load_persona(pan: str) -> dict:
    pan = pan.upper()
    if pan in PERSONAS:
        return copy.deepcopy(PERSONAS[pan])
    # Unknown PAN: behave like a brand-new investor with no KYC anywhere.
    p = _base(pan=pan, name="NEW INVESTOR", kra={"status": "Not found", "agency": "", "reason": "No KYC record for this PAN"},
              ckyc={"found": False, "kin": ""})
    p["aadhaar"]["name"] = "NEW INVESTOR"
    p["bank"]["holder_name"] = "NEW INVESTOR"
    p["_story"] = "Unknown PAN: no record at KRA or CKYC, so the full journey runs."
    return p


# ---- simulated registry calls -------------------------------------------------
def fetch_discovery(profile: dict) -> dict:
    """Step 0: what already exists for this PAN."""
    return {
        "ITD (Income Tax)": f"PAN active · name on PAN: {profile['name']} · PAN–Aadhaar linked: {'Yes' if profile['itd']['pan_aadhaar_linked'] else 'No'}",
        "KRA": f"{profile['kra']['status']}" + (f" at {profile['kra']['agency']}" if profile['kra']['agency'] else "") +
               (f" · reason: {profile['kra']['reason']}" if profile['kra']['reason'] else ""),
        "CKYC (CERSAI)": f"Record found · KIN {profile['ckyc']['kin']}" if profile['ckyc']['found'] else "No CKYC record",
        "CAS (existing folios)": f"{profile['folios']} mutual fund folio(s)" + (" · one folio flagged On Hold" if profile['folio_on_hold'] else ""),
    }
