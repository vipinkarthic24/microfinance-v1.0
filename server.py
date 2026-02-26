from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
from dateutil.relativedelta import relativedelta
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
import sqlite3
import jwt
import bcrypt
from contextlib import contextmanager, asynccontextmanager
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'sv-fincloud-secret-key-2025')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480

# Database path
DB_PATH = ROOT_DIR / 'sv_fincloud.db'

security = HTTPBearer()

# Database connection helper
@contextmanager
def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

# Initialize database
def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL,
                tenant_id TEXT,
                branch_id TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Customers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS customers (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT,
                phone TEXT,
                cibil_score INTEGER,
                created_at TEXT NOT NULL,
                branch_id TEXT,
                tenant_id TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        
        # Branches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS branches (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                location TEXT,
                tenant_id TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Loan types table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loan_types (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                tenant_id TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Interest rates table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interest_rates (
                id TEXT PRIMARY KEY,
                loan_type TEXT NOT NULL,
                category TEXT,
                rate REAL NOT NULL,
                tenant_id TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        # Gold rate table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gold_rate (
                id TEXT PRIMARY KEY,
                rate_per_gram REAL NOT NULL,
                tenant_id TEXT,
                updated_at TEXT NOT NULL
            )
        ''')
        
        # Loans table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS loans (
                id TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                loan_type TEXT NOT NULL,
                amount REAL NOT NULL,
                tenure INTEGER NOT NULL,
                interest_rate REAL NOT NULL,
                emi_amount REAL NOT NULL,
                processing_fee REAL NOT NULL,
                disbursed_amount REAL NOT NULL,
                outstanding_balance REAL NOT NULL,
                status TEXT NOT NULL,
                vehicle_age INTEGER,
                gold_weight REAL,
                approved_by TEXT,
                approved_at TEXT,
                created_at TEXT NOT NULL,
                branch_id TEXT,
                tenant_id TEXT,
                FOREIGN KEY (customer_id) REFERENCES customers(id)
            )
        ''')
        
        # EMI schedule table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emi_schedule (
                id TEXT PRIMARY KEY,
                loan_id TEXT NOT NULL,
                emi_number INTEGER NOT NULL,
                due_date TEXT NOT NULL,
                emi_amount REAL NOT NULL,
                principal_amount REAL NOT NULL,
                interest_amount REAL NOT NULL,
                penalty REAL DEFAULT 0,
                status TEXT NOT NULL,
                paid_at TEXT,
                branch_id TEXT,
                tenant_id TEXT,
                FOREIGN KEY (loan_id) REFERENCES loans(id)
            )
        ''')
        
        # Payments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                loan_id TEXT NOT NULL,
                emi_id TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_date TEXT NOT NULL,
                collected_by TEXT NOT NULL,
                approved_by TEXT,
                approved_at TEXT,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                branch_id TEXT,
                tenant_id TEXT,
                FOREIGN KEY (loan_id) REFERENCES loans(id),
                FOREIGN KEY (emi_id) REFERENCES emi_schedule(id)
            )
        ''')
        
        # Penalties table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS penalties (
                id TEXT PRIMARY KEY,
                loan_id TEXT NOT NULL,
                emi_id TEXT NOT NULL,
                amount REAL NOT NULL,
                reason TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (loan_id) REFERENCES loans(id),
                FOREIGN KEY (emi_id) REFERENCES emi_schedule(id)
            )
        ''')
        
        # Audit logs table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                tenant_id TEXT,
                action TEXT NOT NULL,
                entity_type TEXT NOT NULL,
                entity_id TEXT,
                details TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        conn.commit()
        
        # Create sample users
        create_sample_data(conn)

def create_sample_data(conn):
    cursor = conn.cursor()
    
    # Check if users already exist
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] > 0:
        return
    
    # Hash passwords
    users_data = [
        ('admin', 'admin123', 'admin'),
        ('finance_officer', 'officer123', 'finance_officer'),
        ('collection_agent', 'agent123', 'collection_agent'),
        ('customer', 'customer123', 'customer'),
        ('auditor', 'auditor123', 'auditor')
    ]
    
    tenant_id = str(uuid.uuid4())
    branch_id = str(uuid.uuid4())
    for username, password, role in users_data:
        user_id = str(uuid.uuid4())
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    
        cursor.execute(
            "INSERT INTO users (id, username, password, role, tenant_id, branch_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, username, hashed.decode('utf-8'), role, tenant_id, branch_id, datetime.now(timezone.utc).isoformat())
        )
        # If the sample user is a customer → create basic customer profile
        if role == "customer":
            cursor.execute("""
                INSERT INTO customers
                (id, user_id, name, email, phone, cibil_score, branch_id, tenant_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                user_id,
                "Sample Customer",
                "customer@svfincloud.com",
                "9999999999",
                750,
                branch_id,
                tenant_id,
                datetime.now(timezone.utc).isoformat()
            ))


    # Create default branch
    cursor.execute(
    "INSERT INTO branches (id, name, location, tenant_id, created_at) VALUES (?, ?, ?, ?, ?)",
    (branch_id, 'SV Fincloud Main Branch', 'Mumbai', tenant_id, datetime.now(timezone.utc).isoformat()))
    
    # Create loan types
    loan_types = [
        ('personal_loan', 'Personal Loan'),
        ('vehicle_loan', 'Vehicle Loan'),
        ('gold_loan', 'Gold Loan')
    ]
    
    for lt_id, lt_name in loan_types:
        cursor.execute(
            "INSERT INTO loan_types (id, name, description, tenant_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (lt_id, lt_name, f'{lt_name} for customers', tenant_id, datetime.now(timezone.utc).isoformat()))
    
    # Create interest rates
    interest_rates = [
        ('personal_loan', 'cibil_750_plus', 12.0),
        ('personal_loan', 'cibil_700_749', 15.0),
        ('personal_loan', 'cibil_699', 18.0),
        ('vehicle_loan', 'age_0_3', 11.0),
        ('vehicle_loan', 'age_4_6', 13.0),
        ('vehicle_loan', 'age_7_plus', 15.0),
        ('vehicle_loan', 'age_15_plus', 17.0), 
        ('gold_loan', 'standard', 10.0)
    ]
    
    for loan_type, category, rate in interest_rates:
        cursor.execute(
            "INSERT INTO interest_rates (id, loan_type, category, rate, tenant_id, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), loan_type, category, rate, tenant_id, datetime.now(timezone.utc).isoformat())
)
    
    # Set default gold rate
    cursor.execute(
        "INSERT INTO gold_rate (id, rate_per_gram, tenant_id, updated_at) VALUES (?, ?, ?, ?)",
        (str(uuid.uuid4()), 6500.0, tenant_id, datetime.now(timezone.utc).isoformat())
)
    
    conn.commit()


init_db()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("SV Fincloud Server is starting up...")
    yield
    print("SV Fincloud Server is shutting down safely...")


# ✅ THEN CREATE APP
app = FastAPI(lifespan=lifespan)
api_router = APIRouter(prefix="/api")


# Pydantic Models
class LoginRequest(BaseModel):
    username: str
    password: str
    tenant_id: str
    
class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    tenant_id: str
    branch_id: Optional[str] = None

class LoginResponse(BaseModel):
    token: str
    user: UserResponse

class LoanApplicationRequest(BaseModel):
    loan_type: str
    amount: float
    tenure: int
    monthly_income: float
    vehicle_age: Optional[int] = None
    gold_weight: Optional[float] = None

class PaymentRequest(BaseModel):
    emi_id: str
    amount: float

class ApprovalRequest(BaseModel):
    entity_id: str
    action: str

class UserCreateRequest(BaseModel):
    username: str
    password: str
    role: str
    branch_id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    cibil_score: Optional[int] = None
    model_config = {"extra": "ignore"}

class BranchCreateRequest(BaseModel):
    name: str
    location: str

class InterestRateUpdateRequest(BaseModel):
    loan_type: str
    category: str
    rate: float

class GoldRateUpdateRequest(BaseModel):
    rate_per_gram: float

# Helper functions
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_role(allowed_roles: List[str]):
    def role_checker(token_data: dict = Depends(verify_token)):
        if token_data.get('role') not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return token_data
    return role_checker

def log_audit(conn, user_id: str, tenant_id: str, action: str, entity_type: str, entity_id: str = None, details: str = None):
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO audit_logs 
        (id, user_id, tenant_id, action, entity_type, entity_id, details, created_at) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            str(uuid.uuid4()),
            user_id,
            tenant_id,
            action,
            entity_type,
            entity_id,
            details,
            datetime.now(timezone.utc).isoformat()
        )
    )
def apply_penalty_if_overdue(conn, branch_id, tenant_id):
    cursor = conn.cursor()
    today = datetime.now().date()

    cursor.execute("""
        SELECT id, loan_id, emi_amount, due_date
        FROM emi_schedule
        WHERE status = 'pending'
        AND branch_id = ?
        AND tenant_id = ?
    """, (branch_id, tenant_id))

    emis = cursor.fetchall()

    for emi in emis:
        due_date = datetime.fromisoformat(emi['due_date']).date()
        if today > due_date:
            cursor.execute("SELECT 1 FROM penalties WHERE emi_id = ?", (emi['id'],))
            if cursor.fetchone():
                continue

            penalty_amount = round(emi['emi_amount'] * 0.02, 2)

            cursor.execute("""
                INSERT INTO penalties (id, loan_id, emi_id, amount, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                emi['loan_id'],
                emi['id'],
                penalty_amount,
                "Overdue EMI Penalty (2%)",
                datetime.now(timezone.utc).isoformat()
            ))

            cursor.execute("UPDATE emi_schedule SET penalty = ? WHERE id = ?", (penalty_amount, emi['id']))

# Authentication Routes
@api_router.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (request.username,))
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
        if not bcrypt.checkpw(request.password.encode('utf-8'), user['password'].encode('utf-8')):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        
        token = create_access_token({
            "user_id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "branch_id": user['branch_id'],
            "tenant_id": user['tenant_id']
        })
        user_data = {
            "id": user['id'],
            "username": user['username'],
            "role": user['role'],
            "tenant_id": user['tenant_id'],
            "branch_id": user['branch_id']   
        }

        log_audit(conn, user['id'], user['tenant_id'], 'LOGIN', 'user', user['id'], None)        
        return LoginResponse(token=token, user=UserResponse(**user_data))

@api_router.get("/auth/me")
async def get_current_user(token_data: dict = Depends(verify_token)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """SELECT id, username, role, tenant_id, branch_id
            FROM users
            WHERE id = ? AND tenant_id = ?""",
            (token_data['user_id'], token_data['tenant_id'])
        )        
        user = cursor.fetchone()
        
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        
        return dict(user)

# Customer Routes
@api_router.post("/customer/loan-application")
async def apply_for_loan(request: LoanApplicationRequest, token_data: dict = Depends(require_role(['customer']))):
    with get_db() as conn:
        cursor = conn.cursor()
        branch_id = token_data["branch_id"]

        # 1. Get customer details
        cursor.execute("""
            SELECT id, cibil_score
            FROM customers
            WHERE user_id = ?
            AND branch_id = ?
            AND tenant_id = ?
        """, (token_data['user_id'], token_data["branch_id"], token_data["tenant_id"]))
        customer = cursor.fetchone()
        
        if not customer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer profile not found")
        # 🔥 TENURE VALIDATION
        if request.tenure <= 0 or request.tenure > 24:
            raise HTTPException(
                status_code=400,
                detail="Tenure must be between 1 and 24 months"
            )

       
        # 2. Initialize variables
        interest_rate = 0.0
        loan_status = 'pending' # Default status
        log_details = "Standard application"
        cibil = request.cibil_score if request.cibil_score else (customer['cibil_score'] or 0)

        # 3. Logic for each Loan Type
        if request.loan_type == 'personal_loan':
            # 🔥 CIBIL REQUIRED FOR PERSONAL LOAN
            if not request.cibil_score:
                raise HTTPException(
                    status_code=400,
                    detail="CIBIL score required for personal loan"
                )

            # --- CIBIL EVALUATION ---
            if cibil < 600:
                loan_status = 'rejected'
                log_details = f"Auto-rejected: CIBIL {cibil} is too low"
            elif cibil >= 750:
                loan_status = 'pre-approved'
                log_details = f"Pre-approved: Excellent CIBIL {cibil}"
            else:
                loan_status = 'pending'
                log_details = f"Manual review: CIBIL {cibil} is average"
            
            # Get rate based on CIBIL
            if cibil >= 750:
                category = 'cibil_750_plus'
            elif cibil >= 700:
                category = 'cibil_700_749'
            else:
                category = 'cibil_699'
            cursor.execute("SELECT rate FROM interest_rates WHERE loan_type = ? AND category = ? AND tenant_id = ?",(request.loan_type, category, token_data["tenant_id"]))
            if request.cibil_score:
                cursor.execute(
                    "UPDATE customers SET cibil_score = ? WHERE id = ?",
                    (request.cibil_score, customer['id'])
                )

        elif request.loan_type == 'vehicle_loan':
            if not request.vehicle_age:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vehicle age required")
            
            if request.vehicle_age <= 3:
                category = 'age_0_3'
            elif request.vehicle_age <= 6:
                category = 'age_4_6'
            elif request.vehicle_age <= 10:
                category = 'age_7_plus'
            else:
                category = 'age_15_plus'
            cursor.execute("SELECT rate FROM interest_rates WHERE loan_type = ? AND category = ? AND tenant_id = ?",(request.loan_type, category, token_data["tenant_id"]))

        elif request.loan_type == 'gold_loan':
            # 🔥 VALID GOLD WEIGHT
            if request.gold_weight <= 0 or not request.gold_weight:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid gold weight"
                )
            
            cursor.execute("SELECT rate_per_gram FROM gold_rate WHERE tenant_id = ? ORDER BY updated_at DESC LIMIT 1",(token_data["tenant_id"],))
            gold_rate_row = cursor.fetchone()
            gold_rate = gold_rate_row['rate_per_gram'] if gold_rate_row else 6500.0
            
            max_loan = (request.gold_weight * gold_rate * 0.70)
            if request.amount > max_loan:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Loan amount exceeds 70% of gold value. Max: {max_loan}")
            
            category = 'standard'
            cursor.execute("SELECT rate FROM interest_rates WHERE loan_type = ? AND category = ? AND tenant_id = ?",(request.loan_type, category, token_data["tenant_id"]))

        # 4. Fetch the interest rate from DB
        rate_row = cursor.fetchone()
        if not rate_row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Interest rate not configured for this category")
        
        interest_rate = rate_row['rate']
        
        # 5. Financial Calculations
        total_interest = (request.amount * interest_rate * request.tenure) / (100 * 12)
        total_amount = request.amount + total_interest
        emi_amount = total_amount / request.tenure
        processing_fee = request.amount * 0.05
        disbursed_amount = request.amount - processing_fee

        # 6. EMI Eligibility Check (30% Monthly Income Rule)
        emi_limit = request.monthly_income * 0.30
        if emi_amount <= emi_limit:
            emi_eligible = True
        else:
            emi_eligible = False
        # 🔥 EMI ELIGIBILITY RECOMMENDATION ENGINE
        if not emi_eligible and loan_status != 'rejected':
            recommended_amount = emi_limit * request.tenure

            return {
                "status": "recommendation",
                "recommended_amount": recommended_amount,
                "requested_amount": request.amount
            }

        log_details += f" | EMI Eligible (30% rule): {emi_eligible}"

        # 7. Final Database Insert (ONLY ONE)
        loan_id = str(uuid.uuid4())
        tenant_id = token_data["tenant_id"]
        branch_id = token_data["branch_id"]

        cursor.execute(
            '''INSERT INTO loans (
                id, customer_id, loan_type, amount, tenure, interest_rate, emi_amount,
                processing_fee, disbursed_amount, outstanding_balance, status,
                vehicle_age, gold_weight, created_at, branch_id, tenant_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (
                loan_id, customer['id'], request.loan_type, request.amount, request.tenure,
                interest_rate, emi_amount, processing_fee, disbursed_amount,
                request.amount, loan_status, request.vehicle_age, request.gold_weight,
                datetime.now(timezone.utc).isoformat(), branch_id, tenant_id
            )
        )
        # 7. Audit Log
        log_audit(conn, token_data['user_id'],token_data['tenant_id'], 'LOAN_APPLICATION', 'loan', loan_id, 
                 json.dumps({"amount": request.amount, "type": request.loan_type, "evaluation": log_details}))
        
        return {"message": f"Loan {loan_status} successfully", "loan_id": loan_id, "status": loan_status}

@api_router.get("/customer/loans")
async def get_customer_loans(token_data: dict = Depends(require_role(['customer']))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
                SELECT id FROM customers 
                WHERE user_id = ? AND branch_id = ? AND tenant_id = ?
            """, (token_data['user_id'], token_data["branch_id"], token_data["tenant_id"]))
        customer = cursor.fetchone()
        
        if not customer:
            return []
        
        cursor.execute("""SELECT * FROM loans WHERE customer_id = ? AND branch_id = ? AND tenant_id = ? ORDER BY created_at DESC """, (customer['id'], token_data["branch_id"], token_data["tenant_id"]))
        loans = [dict(row) for row in cursor.fetchall()]
        
        return loans

@api_router.get("/customer/emi-schedule/{loan_id}")
async def get_emi_schedule(loan_id: str, token_data: dict = Depends(require_role(['customer', 'collection_agent', 'finance_officer', 'auditor']))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT e.* FROM emi_schedule e JOIN loans l ON e.loan_id = l.id WHERE e.loan_id = ? AND l.branch_id = ? AND l.tenant_id = ? ORDER BY emi_number", (loan_id,token_data["branch_id"], token_data["tenant_id"]))
        schedule = [dict(row) for row in cursor.fetchall()]
        return schedule

@api_router.get("/customer/payment-history/{loan_id}")
async def get_payment_history(loan_id: str, token_data: dict = Depends(require_role(['customer', 'collection_agent', 'finance_officer', 'auditor']))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT p.* FROM payments p JOIN loans l ON p.loan_id = l.id WHERE p.loan_id = ? AND l.branch_id = ? AND l.tenant_id = ? ORDER BY p.created_at DESC", (loan_id,token_data["branch_id"], token_data["tenant_id"]))
        payments = [dict(row) for row in cursor.fetchall()]
        return payments
        
@api_router.delete("/customer/loans/{loan_id}")
async def delete_loan(loan_id: str, token_data: dict = Depends(require_role(['customer']))):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # 1. First, check if the loan belongs to this customer AND is still pending
        cursor.execute("""
            SELECT l.id, l.status FROM loans l
            INNER JOIN customers c ON l.customer_id = c.id
            WHERE l.id = ? AND c.user_id = ? AND l.branch_id = ? AND l.tenant_id = ?
        """, (loan_id, token_data['user_id'],token_data["branch_id"], token_data["tenant_id"]))
        
        loan = cursor.fetchone()
        
        if not loan:
            raise HTTPException(status_code=404, detail="Loan application not found")
        
        if loan['status'].lower() != 'pending':
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot delete a loan with status: {loan['status']}. Only 'pending' loans can be removed."
            )
        
        # 2. Perform the deletion
        cursor.execute("DELETE FROM emi_schedule WHERE loan_id = ? AND branch_id = ? AND tenant_id = ?", 
               (loan_id, token_data["branch_id"], token_data["tenant_id"]))
        cursor.execute("DELETE FROM payments WHERE loan_id = ? AND branch_id = ? AND tenant_id = ?", 
                    (loan_id, token_data["branch_id"], token_data["tenant_id"]))
        cursor.execute("DELETE FROM loans WHERE id = ? AND branch_id = ? AND tenant_id = ?", 
                    (loan_id, token_data["branch_id"], token_data["tenant_id"]))
        
        # 3. Log the action
        log_audit(conn, token_data['user_id'],token_data['tenant_id'], 'LOAN_DELETED', 'loan', loan_id,None)
        
        return {"message": "Loan application deleted successfully"}
    
@api_router.get("/customer/receipt/{emi_id}")
async def get_emi_receipt(emi_id: str, token_data: dict = Depends(require_role(['customer']))):
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Verify EMI belongs to customer
        cursor.execute("""
            SELECT 
                e.id, e.emi_number, e.emi_amount, e.status,
                l.loan_type, l.id AS loan_id
            FROM emi_schedule e
            JOIN loans l ON e.loan_id = l.id
            JOIN customers c ON l.customer_id = c.id
            WHERE e.id = ? AND c.user_id = ? AND l.branch_id = ? AND l.tenant_id = ?
        """, (emi_id, token_data['user_id'],token_data["branch_id"], token_data["tenant_id"]))

        emi = cursor.fetchone()
        if not emi:
            raise HTTPException(status_code=404, detail="EMI record not found")

        if emi['status'].lower() != 'paid':
            raise HTTPException(status_code=400, detail="Receipt not available")

        # 2. Fetch approved payment
        cursor.execute("""
            SELECT amount, payment_date
            FROM payments
            WHERE emi_id = ? AND status = 'approved'
            AND branch_id = ?
            AND tenant_id = ?
            ORDER BY created_at DESC
            LIMIT 1
        """, (emi_id,token_data["branch_id"], token_data["tenant_id"]))
        payment = cursor.fetchone()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment record not found")

        return {
            "receipt_no": f"REC-{emi['id'][:8].upper()}",
            "loan_id": emi['loan_id'],
            "emi_number": emi['emi_number'],
            "loan_type": emi['loan_type'],
            "amount_paid": payment['amount'],
            "payment_date": payment['payment_date'],
            "status": "SUCCESSFUL"
        }


# Collection Agent Routes
@api_router.get("/agent/customers")
async def get_assigned_customers(token_data: dict = Depends(require_role(['collection_agent']))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DISTINCT 
                c.*, 
                l.id AS loan_id, 
                l.loan_type, 
                l.amount, 
                l.outstanding_balance, 
                l.status
            FROM customers c
            INNER JOIN loans l ON c.id = l.customer_id
            WHERE l.status = 'active'
            AND l.branch_id = ?
            AND l.tenant_id = ?
            ORDER BY c.name
        ''', (token_data["branch_id"], token_data["tenant_id"]))
        return [dict(row) for row in cursor.fetchall()]


@api_router.post("/agent/enter-payment")
async def enter_payment(
    request: PaymentRequest,
    token_data: dict = Depends(require_role(['collection_agent']))
):
    with get_db() as conn:
        cursor = conn.cursor()
        branch_id = token_data["branch_id"]
        tenant_id = token_data["tenant_id"]
        cursor.execute("""
            SELECT e.loan_id
            FROM emi_schedule e
            JOIN loans l ON e.loan_id = l.id
            WHERE e.id = ?
            AND e.status = 'pending'
            AND l.branch_id = ?
            AND l.tenant_id = ?
        """, (request.emi_id, token_data["branch_id"], token_data["tenant_id"]))
        emi = cursor.fetchone()
        if not emi:
            raise HTTPException(status_code=404, detail="EMI not found or not payable")

        payment_id = str(uuid.uuid4())
        cursor.execute("""
            SELECT 1 FROM payments
            WHERE emi_id = ?
            AND status IN ('pending','approved')
            AND branch_id = ?
            AND tenant_id = ?
        """, (request.emi_id, token_data["branch_id"], token_data["tenant_id"]))

        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Payment already exists for this EMI")
        cursor.execute(
            """
            INSERT INTO payments (
                id, loan_id, emi_id, amount,
                status, collected_by, created_at, payment_date, branch_id, tenant_id
            ) VALUES (?, ?, ?, ?, 'pending', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, ?, ?)
            """,
            (
                payment_id,
                emi["loan_id"],
                request.emi_id,
                request.amount,
                token_data["user_id"],
                branch_id,
                tenant_id
            )
        )

        conn.commit()
        return {"message": "Payment submitted for approval"}

# Finance Officer Routes
@api_router.get("/officer/loan-applications")
async def get_loan_applications(token_data: dict = Depends(require_role(['finance_officer']))):
    with get_db() as conn:
        cursor = conn.cursor()
        branch_id = token_data["branch_id"]
        tenant_id = token_data["tenant_id"]
        cursor.execute('''
            SELECT l.*, c.name as customer_name, c.email, c.phone, c.cibil_score
            FROM loans l
            INNER JOIN customers c ON l.customer_id = c.id
            WHERE l.status IN ('pending', 'pre-approved', 'submitted', 'applied')
            AND l.branch_id = ? AND l.tenant_id = ?
            ORDER BY l.created_at DESC
        ''', (branch_id, tenant_id))
        # FIX: You were missing the return value here!
        applications = [dict(row) for row in cursor.fetchall()]
        return applications
    
@api_router.patch("/officer/update-loan/{loan_id}")
async def update_loan_details(loan_id: str, data: dict, token_data: dict = Depends(require_role(['finance_officer', 'admin']))):
    with get_db() as conn:
        cursor = conn.cursor()
        # Example: Updating interest rate or amount before approval
        cursor.execute("""
            SELECT id FROM loans 
            WHERE id = ? AND branch_id = ? AND tenant_id = ?
        """, (loan_id, token_data["branch_id"], token_data["tenant_id"]))

        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail="Loan not found")
        if not data:
            raise HTTPException(status_code=400, detail="No fields provided for update")
        if 'interest_rate' in data:
            cursor.execute("""
                UPDATE loans
                SET interest_rate = ?
                WHERE id = ? AND branch_id = ? AND tenant_id = ?
            """, (data['interest_rate'], loan_id, token_data["branch_id"], token_data["tenant_id"]))
               
        log_audit(conn, token_data['user_id'], token_data['tenant_id'],'LOAN_UPDATED', 'loan', loan_id, json.dumps(data))
        return {"message": "Loan updated successfully"}
    
@api_router.post("/officer/approve-loan")
async def approve_loan(data: dict, token_data: dict = Depends(require_role(['finance_officer']))):
    loan_id = data.get('entity_id')
    action = data.get('action')
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        if action == 'approve':
            try:
                # 1. Update the loan status
                
                cursor.execute('''
                    UPDATE loans 
                    SET status = 'active', 
                        approved_by = ?, 
                        approved_at = CURRENT_TIMESTAMP,
                        outstanding_balance = amount 
                    WHERE id = ? AND branch_id = ? AND tenant_id = ?
                ''', (token_data['user_id'], loan_id, token_data["branch_id"], token_data["tenant_id"]))
                
                # 2. Get details for EMI generation
                cursor.execute("SELECT * FROM loans WHERE id = ? AND branch_id = ? AND tenant_id = ?", (loan_id,token_data["branch_id"], token_data["tenant_id"]))
                loan = cursor.fetchone()
                
                if not loan:
                    raise HTTPException(status_code=404, detail="Loan record not found")
                
                # 3. Create the EMI rows in emi_schedule
                tenure = loan['tenure']
                principal_per_month = loan['amount'] / tenure
                
                for i in range(1, tenure + 1):
                    due_date = (datetime.now() + relativedelta(months=i)).date().isoformat()
                    
                    emi_id = str(uuid.uuid4())

                    cursor.execute('''
                            INSERT INTO emi_schedule (
                                id, loan_id, emi_number,
                                emi_amount, principal_amount, interest_amount,
                                due_date, status, branch_id, tenant_id
                            )
                            VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
                        ''', (
                            emi_id,
                            loan_id,
                            i,
                            loan['emi_amount'],
                            principal_per_month,
                            (loan['emi_amount'] - principal_per_month),
                            due_date,
                            token_data["branch_id"],
                            token_data["tenant_id"]
                        ))

                log_audit(conn, token_data['user_id'], token_data['tenant_id'],'LOAN_APPROVED', 'loan', loan_id,None)
                conn.commit()
                return {"message": "Loan approved successfully"}
                
            except Exception as e:
                conn.rollback() 
                print(f"APPROVE ERROR: {e}")
                raise HTTPException(status_code=500, detail=f"Database Error: {str(e)}")
        else:
            cursor.execute("UPDATE loans SET status = 'rejected' WHERE id = ? AND branch_id = ? AND tenant_id = ?", (loan_id,token_data["branch_id"], token_data["tenant_id"]))

            log_audit(conn, token_data['user_id'], token_data['tenant_id'],'LOAN_REJECTED', 'loan', loan_id,None)

            conn.commit()
            return {"message": "Loan rejected successfully"}
        

@api_router.post("/officer/approve-payment")
async def approve_payment(request: ApprovalRequest, token_data: dict = Depends(require_role(['finance_officer']))):
    with get_db() as conn:
        cursor = conn.cursor()
        branch_id = token_data["branch_id"]
        tenant_id = token_data["tenant_id"]

        # 1️⃣ Fetch Payment Details
        cursor.execute("""
            SELECT * FROM payments 
            WHERE id = ? AND branch_id = ? AND tenant_id = ?
        """, (request.entity_id, branch_id, tenant_id))
        payment = cursor.fetchone()

        if not payment:
            raise HTTPException(status_code=404, detail="Payment record not found")

        # ================= APPROVE PAYMENT =================
        if request.action == 'approve':

            # 2️⃣ Approve payment
            cursor.execute("""
                UPDATE payments 
                SET status = 'approved', approved_by = ?, approved_at = ?
                WHERE id = ? AND branch_id = ? AND tenant_id = ?
            """, (
                token_data['user_id'],
                datetime.now(timezone.utc).isoformat(),
                request.entity_id,
                branch_id,
                tenant_id
            ))

            # 3️⃣ Mark EMI as paid
            cursor.execute("""
                UPDATE emi_schedule
                SET status = 'paid', paid_at = ?
                WHERE id = ? AND branch_id = ? AND tenant_id = ?
            """, (
                datetime.now(timezone.utc).isoformat(),
                payment['emi_id'],
                branch_id,
                tenant_id
            ))

            # 4️⃣ Get EMI principal amount
            cursor.execute("""
                SELECT principal_amount FROM emi_schedule
                WHERE id = ? AND branch_id = ? AND tenant_id = ?
            """, (payment['emi_id'], branch_id, tenant_id))

            emi = cursor.fetchone()
            principal_paid = emi['principal_amount']

            # 5️⃣ Reduce loan outstanding balance
            cursor.execute("""
                UPDATE loans
                SET outstanding_balance = outstanding_balance - ?
                WHERE id = ? AND branch_id = ? AND tenant_id = ?
            """, (principal_paid, payment['loan_id'], branch_id, tenant_id))

            # 6️⃣ Auto close loan if fully paid
            cursor.execute("""
                UPDATE loans
                SET status = 'closed'
                WHERE id = ?
                AND outstanding_balance <= 0
                AND branch_id = ?
                AND tenant_id = ?
            """, (payment['loan_id'], branch_id, tenant_id))
            log_audit(conn, token_data['user_id'], token_data['tenant_id'],'PAYMENT_APPROVED', 'payment', request.entity_id,None)
            conn.commit()
            return {"message": "Payment approved and loan balance updated"}

        # ================= REJECT PAYMENT =================
        elif request.action == 'reject':

            cursor.execute("""
                UPDATE payments
                SET status = 'rejected', approved_by=?, approved_at=?
                WHERE id=? AND branch_id=? AND tenant_id=?
            """, (
                token_data['user_id'],
                datetime.now(timezone.utc).isoformat(),
                request.entity_id,
                branch_id,
                tenant_id
            ))
            log_audit(conn, token_data['user_id'], token_data['tenant_id'],'PAYMENT_REJECTED', 'payment', request.entity_id,None)
            conn.commit()
            return {"message": "Payment rejected"}

        else:
            raise HTTPException(status_code=400, detail="Invalid action")
        
@api_router.get("/officer/analytics-summary")
async def get_analytics(token_data: dict = Depends(require_role(['finance_officer']))):
    with get_db() as conn:
        apply_penalty_if_overdue(conn, token_data["branch_id"], token_data["tenant_id"])
        cursor = conn.cursor()
        
        # Total Collected (Approved Payments)
        cursor.execute("SELECT SUM(amount) as total FROM payments WHERE status = 'approved' AND branch_id = ? AND tenant_id = ?",(token_data["branch_id"], token_data["tenant_id"]))
        collected = cursor.fetchone()['total'] or 0
        
        # Total Pending (EMIs due but not paid)
        cursor.execute("""SELECT SUM(emi_amount + COALESCE(penalty,0)) as total FROM emi_schedule WHERE status = 'pending' AND branch_id = ? AND tenant_id = ?""",(token_data["branch_id"], token_data["tenant_id"]))
        pending = cursor.fetchone()['total'] or 0
        
        
        # Count of Active Loans
        cursor.execute("SELECT COUNT(*) as count FROM loans WHERE status = 'active' AND branch_id = ? AND tenant_id = ?",(token_data["branch_id"], token_data["tenant_id"]))
        active_loans = cursor.fetchone()['count'] or 0

        # Collection Efficiency %
        efficiency = (collected / (collected + pending) * 100) if (collected + pending) > 0 else 0

        return {
            "kpis": {
                "total_collected": collected,
                "total_pending": pending,
                "active_loans": active_loans,
                "efficiency": f"{efficiency:.2f}%"
            }
        }

@api_router.get("/officer/pending-payments")
async def get_pending_payments(token_data: dict = Depends(require_role(['finance_officer']))):
    with get_db() as conn:
        cursor = conn.cursor()
        branch_id = token_data["branch_id"]
        tenant_id = token_data["tenant_id"]
        cursor.execute('''
            SELECT 
                p.id, p.amount, p.created_at as payment_date, p.status,
                l.loan_type, c.name as customer_name,
                COALESCE(e.emi_number, 'Manual') as emi_number
            FROM payments p
            INNER JOIN loans l ON p.loan_id = l.id
            INNER JOIN customers c ON l.customer_id = c.id
            LEFT JOIN emi_schedule e ON p.emi_id = e.id
            WHERE (p.status = 'pending' OR p.status = 'PENDING')
            AND p.branch_id = ? AND p.tenant_id = ?
            ORDER BY p.created_at DESC
        ''', (branch_id, tenant_id))
        payments = [dict(row) for row in cursor.fetchall()]
        return payments
    

# Admin Routes
@api_router.post("/admin/create-user")
async def create_user(request: UserCreateRequest, token_data: dict = Depends(require_role(['admin']))):
    with get_db() as conn:
        cursor = conn.cursor()

        tenant_id = token_data.get("tenant_id")
        if not tenant_id:
            raise HTTPException(status_code=401, detail="Tenant ID missing in token")  
        
        if request.role.lower() == "auditor":
            branch_id = None   # Global auditor
        else:
            branch_id = request.branch_id if request.branch_id else None
 
        if request.role.lower() not in ["admin", "auditor"] and not branch_id:
            raise HTTPException(status_code=400,detail="Branch must be assigned for this role")
        
        # Check username exists
        cursor.execute(
            "SELECT id FROM users WHERE username = ? AND tenant_id = ?",
            (request.username, tenant_id)
        )
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Username already exists")

        # Create user
        user_id = str(uuid.uuid4())
        hashed_password = bcrypt.hashpw(
            request.password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        cursor.execute("""
            INSERT INTO users (id, username, password, role, tenant_id, branch_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id,
            request.username,
            hashed_password,
            request.role.lower(),
            tenant_id,
            branch_id,
            datetime.now(timezone.utc).isoformat()
        ))

        # If customer → create customer record
        if request.role.lower() == "customer":
            if not request.name:
                raise HTTPException(status_code=400, detail="Customer name is required")
             
            cursor.execute("""
                INSERT INTO customers
                (id, user_id, name, email, phone, cibil_score, branch_id, tenant_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(uuid.uuid4()),
                user_id,
                request.name,
                request.email or None,
                request.phone or None,
                int(request.cibil_score) if request.cibil_score is not None else None,
                branch_id,
                tenant_id,
                datetime.now(timezone.utc).isoformat()
            ))

        log_audit(conn,token_data['user_id'],tenant_id,'USER_CREATED','user',user_id,json.dumps({"username": request.username, "role": request.role}))

        return {"message": "User created successfully", "user_id": user_id}

@api_router.get("/admin/users")
async def get_all_users(
    branch_ids: str = None,
    token_data: dict = Depends(require_role(['admin']))
):
    with get_db() as conn:
        cursor = conn.cursor()

        tenant_id = token_data["tenant_id"]

        query = """
            SELECT 
                u.id,
                u.username,
                u.role,
                u.created_at,
                u.branch_id,
                b.name AS branch_name
            FROM users u
            LEFT JOIN branches b ON u.branch_id = b.id
            WHERE u.tenant_id = ?
        """

        params = [tenant_id]

        # 🔥 IF branch filter applied → ONLY branch users
        if branch_ids:
            ids = branch_ids.split(",")

            query += f"""
            AND u.branch_id IN ({",".join("?" * len(ids))})
            """

            params.extend(ids)

        query += " ORDER BY u.created_at DESC"

        cursor.execute(query, params)

        users = [dict(row) for row in cursor.fetchall()]
        return users



@api_router.post("/admin/create-branch")
async def create_branch(request: BranchCreateRequest, token_data: dict = Depends(require_role(['admin']))):
    with get_db() as conn:
        cursor = conn.cursor()
        branch_id = str(uuid.uuid4())
        cursor.execute("""INSERT INTO branches (id, name, location, tenant_id, created_at) VALUES (?, ?, ?, ?, ?)""", 
        (branch_id,request.name,request.location,token_data["tenant_id"],datetime.now(timezone.utc).isoformat()))
        log_audit(conn, token_data['user_id'], token_data['tenant_id'], 'BRANCH_CREATED', 'branch', branch_id,None)
        return {"message": "Branch created successfully", "branch_id": branch_id}

@api_router.get("/admin/branches")
async def get_branches(token_data: dict = Depends(require_role(['admin', 'auditor']))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT * FROM branches WHERE tenant_id = ? ORDER BY created_at DESC""", (token_data["tenant_id"],))
        branches = [dict(row) for row in cursor.fetchall()]
        return branches

@api_router.post("/admin/update-interest-rate")
async def update_interest_rate(request: InterestRateUpdateRequest, token_data: dict = Depends(require_role(['admin']))):
    with get_db() as conn:
        cursor = conn.cursor()
        
        # Check if rate exists
        cursor.execute(
            "SELECT id FROM interest_rates WHERE loan_type = ? AND category = ? AND tenant_id = ?",
            (request.loan_type, request.category, token_data["tenant_id"])
        )
        existing = cursor.fetchone()
        
        if existing:
            cursor.execute("UPDATE interest_rates SET rate = ? WHERE id = ? AND tenant_id = ?",(request.rate, existing['id'], token_data["tenant_id"]))
        else:
            cursor.execute(
            """INSERT INTO interest_rates (id, loan_type, category, rate, tenant_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                request.loan_type,
                request.category,
                request.rate,
                token_data["tenant_id"],
                datetime.now(timezone.utc).isoformat()
            )
        )
        
        log_audit(conn, token_data['user_id'],token_data['tenant_id'], 'INTEREST_RATE_UPDATED', 'interest_rate', None, 
                 json.dumps({"loan_type": request.loan_type, "category": request.category, "rate": request.rate}))
        
        return {"message": "Interest rate updated successfully"}

@api_router.get("/admin/interest-rates")
async def get_interest_rates(token_data: dict = Depends(require_role(['admin', 'finance_officer', 'auditor']))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM interest_rates WHERE tenant_id = ? ORDER BY loan_type, category",
            (token_data["tenant_id"],)
        )
        rates = [dict(row) for row in cursor.fetchall()]
        return rates

@api_router.post("/admin/update-gold-rate")
async def update_gold_rate(request: GoldRateUpdateRequest, token_data: dict = Depends(require_role(['admin']))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO gold_rate (id, rate_per_gram, tenant_id, updated_at) VALUES (?, ?, ?, ?)",
            (str(uuid.uuid4()),request.rate_per_gram,token_data["tenant_id"],datetime.now(timezone.utc).isoformat()))
        
        log_audit(conn, token_data['user_id'], token_data['tenant_id'],'GOLD_RATE_UPDATED', 'gold_rate', None, 
                 json.dumps({"rate": request.rate_per_gram}))
        
        return {"message": "Gold rate updated successfully"}

@api_router.get("/admin/gold-rate")
async def get_gold_rate(token_data: dict = Depends(verify_token)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT * FROM gold_rate WHERE tenant_id = ? ORDER BY updated_at DESC LIMIT 1""",(token_data["tenant_id"],))
        rate = cursor.fetchone()
        return dict(rate) if rate else {"rate_per_gram": 0}

@api_router.get("/admin/stats")
async def get_admin_stats(
    branch_id: str = None,
    token_data: dict = Depends(require_role(['admin']))
):
    with get_db() as conn:
        cursor = conn.cursor()
        tenant_id = token_data["tenant_id"]

        if branch_id:
            cursor.execute("SELECT COUNT(*) as total FROM users WHERE tenant_id = ? AND branch_id = ?", (tenant_id, branch_id))
            total_users = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM customers WHERE tenant_id = ? AND branch_id = ?", (tenant_id, branch_id))
            total_customers = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM loans WHERE status = 'pending' AND branch_id = ? AND tenant_id = ?", (branch_id, tenant_id))
            pending_loans = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM loans WHERE status = 'active' AND branch_id = ? AND tenant_id = ?", (branch_id, tenant_id))
            active_loans = cursor.fetchone()['total']

            cursor.execute("SELECT SUM(amount) as total FROM loans WHERE status = 'active' AND branch_id = ? AND tenant_id = ?", (branch_id, tenant_id))
            total_disbursed = cursor.fetchone()['total'] or 0

            cursor.execute("SELECT SUM(outstanding_balance) as total FROM loans WHERE status = 'active' AND branch_id = ? AND tenant_id = ?", (branch_id, tenant_id))
            total_outstanding = cursor.fetchone()['total'] or 0
        else:
            cursor.execute("SELECT COUNT(*) as total FROM users WHERE tenant_id = ?", (tenant_id,))
            total_users = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM customers WHERE tenant_id = ?", (tenant_id,))
            total_customers = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM loans WHERE status = 'pending' AND tenant_id = ?", (tenant_id,))
            pending_loans = cursor.fetchone()['total']

            cursor.execute("SELECT COUNT(*) as total FROM loans WHERE status = 'active' AND tenant_id = ?", (tenant_id,))
            active_loans = cursor.fetchone()['total']

            cursor.execute("SELECT SUM(amount) as total FROM loans WHERE status = 'active' AND tenant_id = ?", (tenant_id,))
            total_disbursed = cursor.fetchone()['total'] or 0

            cursor.execute("SELECT SUM(outstanding_balance) as total FROM loans WHERE status = 'active' AND tenant_id = ?", (tenant_id,))
            total_outstanding = cursor.fetchone()['total'] or 0

        return {
            "total_users": total_users,
            "total_customers": total_customers,
            "pending_loans": pending_loans,
            "approved_loans": active_loans,
            "total_disbursed": total_disbursed,
            "total_outstanding": total_outstanding
        }
@api_router.get("/admin/interest-earned")
async def get_interest_earned(
    branch_id: str = None,
    token_data: dict = Depends(require_role(['admin']))
):
    with get_db() as conn:
        cursor = conn.cursor()
        tenant_id = token_data["tenant_id"]

        if branch_id:
            cursor.execute("""
                SELECT SUM(interest_amount) as total_interest
                FROM emi_schedule
                WHERE status = 'paid'
                AND tenant_id = ?
                AND branch_id = ?
            """, (tenant_id, branch_id))
        else:
            cursor.execute("""
                SELECT SUM(interest_amount) as total_interest
                FROM emi_schedule
                WHERE status = 'paid'
                AND tenant_id = ?
            """, (tenant_id,))

        total = cursor.fetchone()['total_interest'] or 0
        return {"interest_earned": total}
    
@api_router.get("/admin/branch-loan-stats")
async def branch_loan_stats(token_data: dict = Depends(require_role(['admin']))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.name as branch, SUM(l.amount) as amount
            FROM loans l
            JOIN branches b ON l.branch_id = b.id
            WHERE l.status = 'active'
            AND l.tenant_id = ?
            GROUP BY b.name
        """, (token_data["tenant_id"],))
        return [dict(row) for row in cursor.fetchall()]

@api_router.get("/admin/monthly-collections")
async def monthly_collections(token_data: dict = Depends(require_role(['admin']))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT strftime('%Y-%m', payment_date) as month,
                   SUM(amount) as amount
            FROM payments
            WHERE status = 'approved'
            AND tenant_id = ?
            GROUP BY month
            ORDER BY month
        """, (token_data["tenant_id"],))
        return [dict(row) for row in cursor.fetchall()]

@api_router.get("/admin/branch-performance")
async def branch_performance(token_data: dict = Depends(require_role(['admin']))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT b.name as branch, SUM(p.amount) as collected
            FROM payments p
            JOIN loans l ON p.loan_id = l.id
            JOIN branches b ON l.branch_id = b.id
            WHERE p.status = 'approved'
            AND p.tenant_id = ?
            GROUP BY b.name
            ORDER BY collected DESC
        """, (token_data["tenant_id"],))
        return [dict(row) for row in cursor.fetchall()]


    
# Auditor Routes
@api_router.get("/auditor/loans")
async def get_all_loans(token_data: dict = Depends(require_role(['auditor', 'admin']))):

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT l.*, c.name as customer_name, c.email, c.phone
            FROM loans l
            INNER JOIN customers c ON l.customer_id = c.id
            WHERE l.tenant_id = ?
            ORDER BY l.created_at DESC
        """, (token_data["tenant_id"],))
        loans = [dict(row) for row in cursor.fetchall()]
        return loans

@api_router.get("/auditor/payments")
async def get_all_payments(token_data: dict = Depends(require_role(['auditor', 'admin']))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, l.loan_type, c.name as customer_name
            FROM payments p
            INNER JOIN loans l ON p.loan_id = l.id
            INNER JOIN customers c ON l.customer_id = c.id
            WHERE p.tenant_id = ?
            ORDER BY p.created_at DESC
        """, (token_data["tenant_id"],))
        payments = [dict(row) for row in cursor.fetchall()]
        return payments

@api_router.get("/auditor/audit-logs")
async def get_audit_logs(token_data: dict = Depends(require_role(['auditor', 'admin']))):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""SELECT a.*, u.username FROM audit_logs a LEFT JOIN users u ON a.user_id = u.id WHERE a.tenant_id = ? ORDER BY a.created_at DESC LIMIT 500
        """, (token_data["tenant_id"],))
        logs = [dict(row) for row in cursor.fetchall()]
        return logs

# Common Routes
@api_router.get("/loan-types")
async def get_loan_types(token_data: dict = Depends(verify_token)):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM loan_types WHERE tenant_id = ?", (token_data["tenant_id"],))
        types = [dict(row) for row in cursor.fetchall()]
        return types
@api_router.get("/debug/users")
def debug_users():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, role FROM users")
        return [dict(row) for row in cursor.fetchall()]
@api_router.get("/debug/reset-admin")
def reset_admin_password():
    with get_db() as conn:
        cursor = conn.cursor()
        new_hash = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        cursor.execute("UPDATE users SET password = ? WHERE username = 'admin'", (new_hash,))
        conn.commit()
        return {"message": "Admin password reset to admin123"}
# Include router
app.include_router(api_router)
app.add_middleware(
    CORSMiddleware,
    # Change this to trust your local frontend specifically
    allow_origins=["http://localhost:3000"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

