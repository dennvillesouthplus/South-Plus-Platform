"""SQLite persistence for synthetic SafiriCare demonstration records."""
import json
import os
import sqlite3
import uuid
from datetime import datetime, timezone

DB_PATH = os.getenv('SAFIRI_DB', os.path.join(os.path.dirname(__file__), 'demo.db'))
STAGES = ['Registration', 'Referral', 'Facility response', 'Consultation / testing', 'Prescription', 'Pharmacy collection', 'Follow-up']
ROLES = ['Community worker', 'Clinic / hospital', 'Laboratory', 'Pharmacy', 'Administrator', 'Patient']


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def connect():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn


def initialize():
    with connect() as db:
        db.execute('CREATE TABLE IF NOT EXISTS cases (id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, stage INTEGER NOT NULL, status TEXT NOT NULL, data TEXT NOT NULL)')
        db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, at TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, details TEXT NOT NULL, FOREIGN KEY(case_id) REFERENCES cases(id))')


def case_id(prefix):
    return f'{prefix}-{uuid.uuid4().hex[:8].upper()}'


def get_case(identifier):
    with connect() as db:
        row = db.execute('SELECT * FROM cases WHERE id=?', (identifier,)).fetchone()
    if row is None:
        raise ValueError('Case not found')
    result = dict(row)
    result['data'] = json.loads(result['data'])
    return result


def list_cases():
    with connect() as db:
        rows = db.execute('SELECT id,created_at,updated_at,stage,status,data FROM cases ORDER BY updated_at DESC').fetchall()
    return [{**dict(row), 'data': json.loads(row['data'])} for row in rows]


def history(identifier):
    with connect() as db:
        rows = db.execute('SELECT at,actor,action,details FROM events WHERE case_id=? ORDER BY id DESC', (identifier,)).fetchall()
    return [dict(row) for row in rows]


def create_case(name, concern, consent, actor):
    if not consent:
        raise ValueError('Recorded consent is required for this demonstration')
    if not name.strip() or not concern.strip():
        raise ValueError('Name and presenting concern are required')
    identifier = case_id('PAT')
    data = {'name': name.strip(), 'concern': concern.strip(), 'consent': True, 'facility': '', 'referral_status': '', 'appointment': '', 'wait_minutes': 0, 'consultation_notes': '', 'lab_request_id': '', 'lab_test': '', 'lab_result': '', 'lab_verified_by': '', 'medication': '', 'prescription_id': '', 'quantity_prescribed': 0, 'quantity_dispensed': 0, 'dispensing_events': [], 'patient_status': '', 'next_check': '', 'followup_note': ''}
    timestamp = now()
    with connect() as db:
        db.execute('INSERT INTO cases VALUES (?,?,?,?,?,?)', (identifier,timestamp,timestamp,1,'Registered',json.dumps(data)))
        db.execute('INSERT INTO events(case_id,at,actor,action,details) VALUES (?,?,?,?,?)', (identifier,timestamp,actor,'Registration',f'Consent recorded; concern: {concern.strip()}'))
    return identifier


def update_case(identifier, actor, action, changes, *, expected_stages, next_stage, status, details=''):
    with connect() as db:
        row = db.execute('SELECT stage,data FROM cases WHERE id=?', (identifier,)).fetchone()
        if row is None:
            raise ValueError('Case not found')
        if row['stage'] not in expected_stages:
            raise ValueError(f'Cannot perform {action} at this stage')
        data = json.loads(row['data'])
        data.update(changes)
        timestamp = now()
        db.execute('UPDATE cases SET updated_at=?,stage=?,status=?,data=? WHERE id=?', (timestamp,next_stage,status,json.dumps(data),identifier))
        db.execute('INSERT INTO events(case_id,at,actor,action,details) VALUES (?,?,?,?,?)', (identifier,timestamp,actor,action,details))


def perform(identifier, role, action, **values):
    """Demonstration role gate; NOT authentication or authorization."""
    permitted = {
        'refer': ['Community worker'], 'respond': ['Clinic / hospital'],
        'consult': ['Clinic / hospital'], 'lab': ['Laboratory'],
        'prescribe': ['Clinic / hospital'], 'dispense': ['Pharmacy'],
        'followup': ['Community worker']
    }
    if action not in permitted:
        raise ValueError('Unknown action')
    if role not in permitted[action] and role != 'Administrator':
        raise PermissionError(f'{action} requires {permitted[action][0]} role')
    case = get_case(identifier)
    data = case['data']
    stage = case['stage']
    if action == 'refer':
        facility = values.get('facility','').strip()
        if not facility:
            raise ValueError('Receiving facility is required')
        update_case(identifier,role,'Referral sent',{'facility':facility,'referral_status':'Pending'},expected_stages=[1,2],next_stage=2,status='Awaiting facility',details=facility)
    elif action == 'respond':
        decision = values.get('decision')
        if decision == 'Redirect':
            target = values.get('redirect_to','').strip()
            if not target:
                raise ValueError('New facility is required')
            update_case(identifier,role,'Referral redirected',{'facility':target,'referral_status':'Pending'},expected_stages=[2],next_stage=2,status='Awaiting redirected facility',details=target)
        elif decision == 'Accept':
            appointment = values.get('appointment','').strip()
            if not appointment:
                raise ValueError('Appointment is required')
            wait = int(values.get('wait_minutes',0))
            if wait < 0:
                raise ValueError('Wait cannot be negative')
            update_case(identifier,role,'Referral accepted',{'referral_status':'Accepted','appointment':appointment,'wait_minutes':wait},expected_stages=[2],next_stage=3,status='Appointment scheduled',details=appointment)
        else:
            raise ValueError('Choose Accept or Redirect')
    elif action == 'consult':
        notes = values.get('notes','').strip()
        if not notes:
            raise ValueError('Consultation notes required')
        needs_lab = bool(values.get('needs_lab',True))
        test = values.get('test','').strip()
        if needs_lab and not test:
            raise ValueError('Test description required')
        changes = {'consultation_notes':notes,'lab_test':test if needs_lab else '', 'lab_request_id':case_id('LAB') if needs_lab else ''}
        update_case(identifier,role,'Consultation recorded',changes,expected_stages=[3],next_stage=4 if needs_lab else 5,status='Awaiting laboratory' if needs_lab else 'Ready for prescription',details='Test requested' if needs_lab else 'No laboratory test requested')
    elif action == 'lab':
        request = values.get('request_id','').strip()
        result = values.get('result','').strip()
        verifier = values.get('verifier','').strip()
        if request != data['lab_request_id'] or not request:
            raise ValueError('Laboratory request ID does not match')
        if not result or not verifier:
            raise ValueError('Verified result and verifier required')
        update_case(identifier,role,'Laboratory result verified',{'lab_result':result,'lab_verified_by':verifier},expected_stages=[4],next_stage=5,status='Ready for prescription',details=f'Request {request} verified by {verifier}')
    elif action == 'prescribe':
        medication = values.get('medication','').strip()
        quantity = int(values.get('quantity',0))
        if not medication or quantity <= 0:
            raise ValueError('Medication and positive quantity required')
        update_case(identifier,role,'Prescription authorised',{'medication':medication,'quantity_prescribed':quantity,'prescription_id':case_id('RX')},expected_stages=[5],next_stage=6,status='Awaiting pharmacy',details=f'{medication}; quantity {quantity}')
    elif action == 'dispense':
        rx = values.get('prescription_id','').strip()
        pharmacy = values.get('pharmacy','').strip()
        quantity = int(values.get('quantity',0))
        remaining = data['quantity_prescribed'] - data['quantity_dispensed']
        if rx != data['prescription_id'] or not rx:
            raise ValueError('Prescription ID does not match')
        if not pharmacy or quantity <= 0 or quantity > remaining:
            raise ValueError(f'Enter a pharmacy and quantity between 1 and {remaining}')
        total = data['quantity_dispensed'] + quantity
        events = data['dispensing_events'] + [{'pharmacy':pharmacy,'quantity':quantity,'at':now()}]
        complete = total == data['quantity_prescribed']
        update_case(identifier,role,'Medication dispensed',{'quantity_dispensed':total,'dispensing_events':events},expected_stages=[6],next_stage=7 if complete else 6,status='Awaiting follow-up' if complete else 'Partially dispensed',details=f'{pharmacy}: {quantity} units; {total}/{data["quantity_prescribed"]}')
    elif action == 'followup':
        patient_status = values.get('patient_status','').strip()
        note = values.get('note','').strip()
        close = bool(values.get('close',False))
        next_check = values.get('next_check','').strip()
        if not patient_status or not note:
            raise ValueError('Patient status and follow-up note required')
        if not close and not next_check:
            raise ValueError('Next check date required for ongoing care')
        update_case(identifier,role,'Follow-up completed',{'patient_status':patient_status,'followup_note':note,'next_check': '' if close else next_check},expected_stages=[7,8],next_stage=9 if close else 8,status='Closed' if close else 'Follow-up ongoing',details=f'{patient_status}; {note}')
