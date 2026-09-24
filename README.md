# IFANOW · Investor Onboarding Prototype

A simple, app-style onboarding flow (like opening an account on Groww or Zerodha) that demonstrates the KYC design from my IFANOW Product Intern assignment.

> Prototype with demo data only. Every PAN and name is fictional, and the checks against the Income Tax Dept, KRA, DigiLocker, the bank (₹1 penny drop), depositories and Account Aggregator are simulated. **The OTP is always `123456`.**

## The flow (one screen per step)

Welcome → Mobile OTP → Email OTP → **PAN check** → *(Aadhaar via DigiLocker → Selfie)* → Your details → Nominee → Bank (₹1 check) → PMS (optional) → Review & eSign → Done

What the design does differently:
- **PAN first.** If your KYC already exists, the Aadhaar and selfie steps are skipped (8 steps instead of 10).
- **No dead ends.** If your Aadhaar-linked mobile doesn't work, you can use an offline Aadhaar file or a 2-minute video call.
- **Names checked before submission.** Small differences between PAN, Aadhaar and bank ask for a one-tap confirmation, so nothing gets rejected later.
- **PMS is optional.** Mutual funds are ready straight away. PMS (₹50L+) can be unlocked now or later with a demat link and Account Aggregator. A demat name mismatch pauses only PMS.
- **Adapts to you.** NRIs must use NRE/NRO accounts, US tax residents only see fund houses that accept them, and companies/HUFs get an entity documents step.

## Demo PANs

| PAN | What you'll see |
|---|---|
| `ABCPS1234K` | KYC already verified, so the short journey |
| `AKIPI9753R` | Name spelled differently on Aadhaar and demat |
| `AFRPR5678L` | Aadhaar-linked mobile not working, so the fallback appears |
| `AKNPM4321Q` | NRI living in the US |
| `AADCA1357P` | Company PAN, so the entity documents step appears |
| any other valid PAN | Brand-new investor |

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy (free)

Push this folder to a public GitHub repo, then on **share.streamlit.io** choose **Create app**, pick the repo, branch `main` and file `app.py`, and click **Deploy**.

## Files

```
app.py              The onboarding screens
engine/pan.py       PAN validation; holder type from the 4th character (P = person, C = company, H = HUF…)
engine/matching.py  Name matching across documents (initials, word order, Pvt/Ltd) with accept / confirm / fix actions
engine/data.py      Demo investors and simulated registry responses
.streamlit/         IFANOW green theme
```
