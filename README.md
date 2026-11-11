# SafiriCare — Python interactive web prototype

A Streamlit-based recreation of the seven-stage care journey dashboard. **Synthetic demonstrations only.** No real patient data.

## Start in PyCharm (Windows)

1. Open this extracted folder as a project.
2. In PyCharm Terminal, run:

```powershell
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

3. Open the localhost URL printed in the terminal (usually `http://localhost:8501`).

Or double-click `start_windows.bat` after installing Python.

## Test scenario

1. Select **Community worker** → **Register patient**; enter `Example Patient A`, `Fever and fatigue`, check consent.
2. Open **Patient journey**; as Community worker, send referral to `District Clinic A`.
3. Select **Clinic / hospital**; accept the referral (or redirect it to another clinic), then record a consultation and request a laboratory test.
4. Select **Laboratory**; verify the displayed request ID and record a fictional result.
5. Select **Clinic / hospital**; authorise a synthetic prescription of 10 units.
6. Select **Pharmacy**; dispense 6 units, then 4 units, observing the partial-dispensing state.
7. Select **Community worker**; record follow-up and close the case, or schedule another check.
8. Visit **Activity history** to inspect and export the synthetic event log.

You can skip laboratory testing by unchecking the test requirement during consultation.

## Data and limitations

The demo stores fictional records in a local SQLite file `demo.db` (created on first run). Delete that file to reset all demonstration cases. You can override the location with the `SAFIRI_DB` environment variable.

**Not for clinical or production use.** The role selector is a UI simulation, not authentication; no identity verification, permissions, encryption at rest, clinical validation, interoperability or regulated medical-data controls are implemented. Do not expose this app publicly or use real patient information. A real deployment requires a secured backend, authenticated provider accounts, organisation and patient-level access rules, robust audit integrity, appropriate hosting, legal review, consent and retention policies, and clinical safety assessment.
