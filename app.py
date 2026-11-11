"""South-Plus interactive synthetic-care demonstration. Run: streamlit run app.py"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from store import ROLES, initialize, create_case, list_cases, get_case, history, perform

st.set_page_config(page_title='SafiriCare | Care coordination', page_icon='🩺', layout='wide')
initialize()
st.markdown('''<style>
.block-container {padding-top: 1.5rem; max-width: 1400px}
.hero {padding: 22px 26px; border-radius: 16px; background: #103e4a; color: white; margin-bottom: 22px}
.hero h1 {color: white; margin: 0; font-size: 2rem}
.hero p {color: #cce4e6; margin: 5px 0 0}
[data-testid="stMetric"] {background:#f3f8f9; padding:15px; border-radius:12px}
</style>''', unsafe_allow_html=True)
st.markdown('<div class="hero"><h1>SafiriCare</h1><p>Connected care journey · Synthetic demonstration environment</p></div>', unsafe_allow_html=True)
st.warning('DEMO ONLY — Use fictional patient details. Role selection is not secure login. Do not enter real medical information.', icon='⚠️')

with st.sidebar:
    st.title('Workspace')
    role = st.selectbox('Demonstration role', ROLES)
    page = st.radio('Navigate', ['Dashboard', 'Register patient', 'Patient journey', 'Activity history'], label_visibility='collapsed')
    st.divider()
    st.caption('SQLite demo persistence · No real integrations · No production access controls')

cases = list_cases()
case_map = {f"{c['id']} · {c['data']['name']}": c['id'] for c in cases}

def choose_case(key):
    if not case_map:
        st.info('No cases yet. Register a fictional patient first.')
        return None
    selected = st.selectbox('Select fictional patient', list(case_map), key=key)
    return get_case(case_map[selected])

def action_call(identifier, action, **kwargs):
    try:
        perform(identifier, role, action, **kwargs)
        st.success('Action recorded successfully.')
        st.rerun()
    except (ValueError, PermissionError) as exc:
        st.error(str(exc))

if page == 'Dashboard':
    st.header('Care coordination overview')
    a,b,c,d = st.columns(4)
    a.metric('Patient records', len(cases))
    b.metric('Open journeys', sum(x['status'] != 'Closed' for x in cases))
    c.metric('Closed journeys', sum(x['status'] == 'Closed' for x in cases))
    d.metric('Pending referrals', sum(x['stage'] == 2 for x in cases))
    st.subheader('Patient journeys')
    if cases:
        st.dataframe(pd.DataFrame([{'Case ID':x['id'],'Patient (fictional)':x['data']['name'],'Facility':x['data']['facility'] or '—','Status':x['status'],'Stage':x['stage'],'Updated (UTC)':x['updated_at']} for x in cases]),hide_index=True,use_container_width=True)
    else:
        st.info('Register a fictional patient to begin the care pathway.')
    st.markdown('**Care pathway:** Registration → Referral → Facility response → Consultation / testing → Prescription → Pharmacy collection → Follow-up')

elif page == 'Register patient':
    st.header('Patient registration')
    if role not in ('Community worker','Administrator'):
        st.info('Switch to Community worker to register a patient.')
    else:
        with st.form('registration',clear_on_submit=True):
            name = st.text_input('Fictional patient name', placeholder='Example Patient A')
            concern = st.text_area('Presenting concern', placeholder='Fever and fatigue')
            consent = st.checkbox('Fictional patient consent recorded for this demonstration')
            submitted = st.form_submit_button('Create care record', type='primary')
        if submitted:
            try:
                identifier = create_case(name,concern,consent,role)
                st.success(f'Created case {identifier}. Open Patient journey to continue.')
            except ValueError as exc:
                st.error(str(exc))

elif page == 'Patient journey':
    st.header('Patient journey')
    case = choose_case('journey_case')
    if case:
        data = case['data']; stage = case['stage']; identifier = case['id']
        x,y,z = st.columns(3)
        x.metric('Case',identifier); y.metric('Current status',case['status']); z.metric('Journey stage',f'{min(stage,7)} / 7')
        st.progress(min(stage,7)/7)
        with st.expander('Patient and care record', expanded=False):
            st.json({'id':identifier,**data})
        if stage == 1:
            st.subheader('2 · Referral')
            if role in ('Community worker','Administrator'):
                with st.form('referral'):
                    facility = st.text_input('Receiving facility', 'District Clinic A')
                    if st.form_submit_button('Send referral',type='primary'):
                        action_call(identifier,'refer',facility=facility)
            else: st.info('Community worker action required.')
        elif stage == 2:
            st.subheader('3 · Facility response')
            st.write(f"Referral to **{data['facility']}**")
            if role in ('Clinic / hospital','Administrator'):
                with st.form('response'):
                    decision = st.radio('Decision',['Accept','Redirect'],horizontal=True)
                    appointment = st.text_input('Appointment date/time', (datetime.now()+timedelta(days=1)).strftime('%Y-%m-%d 09:00'))
                    wait = st.number_input('Estimated wait (minutes)',0,1000,30)
                    redirect = st.text_input('Alternative facility (if redirecting)')
                    if st.form_submit_button('Record facility response',type='primary'):
                        action_call(identifier,'respond',decision=decision,appointment=appointment,wait_minutes=wait,redirect_to=redirect)
            else: st.info('Clinic / hospital action required.')
        elif stage == 3:
            st.subheader('4 · Consultation and testing')
            if role in ('Clinic / hospital','Administrator'):
                with st.form('consult'):
                    notes = st.text_area('Consultation notes', 'Synthetic clinical assessment completed.')
                    needs_lab = st.checkbox('Laboratory test required',value=True)
                    test = st.text_input('Test requested', 'Example diagnostic test')
                    if st.form_submit_button('Save consultation',type='primary'):
                        action_call(identifier,'consult',notes=notes,needs_lab=needs_lab,test=test)
            else: st.info('Clinic / hospital action required.')
        elif stage == 4:
            st.subheader('4 · Laboratory verification')
            st.info(f"Requested test: {data['lab_test']} · Request ID: {data['lab_request_id']}")
            if role in ('Laboratory','Administrator'):
                with st.form('lab'):
                    request = st.text_input('Confirm laboratory request ID',value=data['lab_request_id'])
                    result = st.text_area('Verified test result', 'Example result: verified')
                    verifier = st.text_input('Verifier name', 'Laboratory Officer A')
                    if st.form_submit_button('Verify laboratory result',type='primary'):
                        action_call(identifier,'lab',request_id=request,result=result,verifier=verifier)
            else: st.info('Laboratory action required.')
        elif stage == 5:
            st.subheader('5 · Prescription')
            if role in ('Clinic / hospital','Administrator'):
                with st.form('prescription'):
                    medication = st.text_input('Example medication', 'Demo medication (not medical advice)')
                    quantity = st.number_input('Quantity prescribed',min_value=1,value=10)
                    if st.form_submit_button('Authorise prescription',type='primary'):
                        action_call(identifier,'prescribe',medication=medication,quantity=quantity)
            else: st.info('Clinic / hospital action required.')
        elif stage == 6:
            st.subheader('6 · Pharmacy collection')
            remaining = data['quantity_prescribed']-data['quantity_dispensed']
            st.info(f"Prescription: {data['prescription_id']} · {data['medication']} · Dispensed {data['quantity_dispensed']} / {data['quantity_prescribed']}")
            if role in ('Pharmacy','Administrator'):
                with st.form('dispensing'):
                    rx = st.text_input('Verify prescription ID',value=data['prescription_id'])
                    pharmacy = st.text_input('Supplying pharmacy','Pharmacy A')
                    qty = st.number_input('Quantity to dispense',min_value=1,max_value=remaining,value=remaining)
                    if st.form_submit_button('Record dispensing',type='primary'):
                        action_call(identifier,'dispense',prescription_id=rx,pharmacy=pharmacy,quantity=qty)
            else: st.info('Pharmacy action required.')
        elif stage in (7,8):
            st.subheader('7 · Follow-up')
            if role in ('Community worker','Administrator'):
                with st.form('followup'):
                    patient_status = st.selectbox('Patient status',['Improving','Stable','Needs further care','Recovered'])
                    note = st.text_area('Visit note','Follow-up completed (fictional).')
                    close = st.checkbox('Close this care journey',value=False)
                    next_check = st.date_input('Next check date',datetime.now().date()+timedelta(days=7)).isoformat()
                    if st.form_submit_button('Record follow-up',type='primary'):
                        action_call(identifier,'followup',patient_status=patient_status,note=note,close=close,next_check=next_check)
            else: st.info('Community worker action required.')
        else:
            st.success('Care journey closed. All completed events remain in the activity history.')
        st.subheader('Recent activity')
        for event in history(identifier)[:5]:
            st.caption(f"{event['at']} · {event['actor']} · {event['action']} — {event['details']}")

elif page == 'Activity history':
    st.header('Activity history')
    case = choose_case('history_case')
    if case:
        records = history(case['id'])
        st.dataframe(pd.DataFrame(records),hide_index=True,use_container_width=True)
        st.download_button('Export synthetic activity history (CSV)',pd.DataFrame(records).to_csv(index=False),'synthetic_case_history.csv','text/csv')
