import requests
import sys
import json
from datetime import datetime

class SVFincloudAPITester:
    def __init__(self, base_url="https://loan-manager-app-6.preview.emergentagent.com/api"):
        self.base_url = base_url
        self.tokens = {}
        self.users = {}
        self.tests_run = 0
        self.tests_passed = 0
        self.loan_ids = []
        self.payment_ids = []

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login(self, username, password, role):
        """Test login for different roles"""
        success, response = self.run_test(
            f"Login as {role}",
            "POST",
            "auth/login",
            200,
            data={"username": username, "password": password}
        )
        if success and 'token' in response:
            self.tokens[role] = response['token']
            self.users[role] = response['user']
            return True
        return False

    def test_auth_me(self, role):
        """Test /auth/me endpoint"""
        success, response = self.run_test(
            f"Get current user ({role})",
            "GET",
            "auth/me",
            200,
            token=self.tokens.get(role)
        )
        return success

    def test_customer_loan_application(self, loan_type, amount, tenure, **kwargs):
        """Test loan application"""
        data = {
            "loan_type": loan_type,
            "amount": amount,
            "tenure": tenure
        }
        data.update(kwargs)
        
        success, response = self.run_test(
            f"Apply for {loan_type} loan",
            "POST",
            "customer/loan-application",
            200,
            data=data,
            token=self.tokens.get('customer')
        )
        if success and 'loan_id' in response:
            self.loan_ids.append(response['loan_id'])
        return success, response

    def test_get_customer_loans(self):
        """Test getting customer loans"""
        success, response = self.run_test(
            "Get customer loans",
            "GET",
            "customer/loans",
            200,
            token=self.tokens.get('customer')
        )
        return success, response

    def test_finance_officer_loan_applications(self):
        """Test getting pending loan applications"""
        success, response = self.run_test(
            "Get pending loan applications",
            "GET",
            "officer/loan-applications",
            200,
            token=self.tokens.get('finance_officer')
        )
        return success, response

    def test_approve_loan(self, loan_id, action='approve'):
        """Test loan approval/rejection"""
        success, response = self.run_test(
            f"Loan {action}",
            "POST",
            "officer/approve-loan",
            200,
            data={"entity_id": loan_id, "action": action},
            token=self.tokens.get('finance_officer')
        )
        return success

    def test_get_emi_schedule(self, loan_id, role='customer'):
        """Test getting EMI schedule"""
        success, response = self.run_test(
            f"Get EMI schedule ({role})",
            "GET",
            f"customer/emi-schedule/{loan_id}",
            200,
            token=self.tokens.get(role)
        )
        return success, response

    def test_collection_agent_customers(self):
        """Test getting assigned customers"""
        success, response = self.run_test(
            "Get assigned customers",
            "GET",
            "agent/customers",
            200,
            token=self.tokens.get('collection_agent')
        )
        return success, response

    def test_enter_payment(self, emi_id, amount):
        """Test entering payment"""
        success, response = self.run_test(
            "Enter payment",
            "POST",
            "agent/enter-payment",
            200,
            data={"emi_id": emi_id, "amount": amount},
            token=self.tokens.get('collection_agent')
        )
        if success and 'payment_id' in response:
            self.payment_ids.append(response['payment_id'])
        return success, response

    def test_pending_payments(self):
        """Test getting pending payments"""
        success, response = self.run_test(
            "Get pending payments",
            "GET",
            "officer/pending-payments",
            200,
            token=self.tokens.get('finance_officer')
        )
        return success, response

    def test_approve_payment(self, payment_id, action='approve'):
        """Test payment approval"""
        success, response = self.run_test(
            f"Payment {action}",
            "POST",
            "officer/approve-payment",
            200,
            data={"entity_id": payment_id, "action": action},
            token=self.tokens.get('finance_officer')
        )
        return success

    def test_admin_stats(self):
        """Test admin dashboard stats"""
        success, response = self.run_test(
            "Get admin stats",
            "GET",
            "admin/stats",
            200,
            token=self.tokens.get('admin')
        )
        return success, response

    def test_create_user(self, username, password, role, **kwargs):
        """Test creating new user"""
        data = {
            "username": username,
            "password": password,
            "role": role
        }
        data.update(kwargs)
        
        success, response = self.run_test(
            f"Create {role} user",
            "POST",
            "admin/create-user",
            200,
            data=data,
            token=self.tokens.get('admin')
        )
        return success

    def test_create_branch(self, name, location):
        """Test creating branch"""
        success, response = self.run_test(
            "Create branch",
            "POST",
            "admin/create-branch",
            200,
            data={"name": name, "location": location},
            token=self.tokens.get('admin')
        )
        return success

    def test_update_gold_rate(self, rate):
        """Test updating gold rate"""
        success, response = self.run_test(
            "Update gold rate",
            "POST",
            "admin/update-gold-rate",
            200,
            data={"rate_per_gram": rate},
            token=self.tokens.get('admin')
        )
        return success

    def test_update_interest_rate(self, loan_type, category, rate):
        """Test updating interest rate"""
        success, response = self.run_test(
            "Update interest rate",
            "POST",
            "admin/update-interest-rate",
            200,
            data={"loan_type": loan_type, "category": category, "rate": rate},
            token=self.tokens.get('admin')
        )
        return success

    def test_auditor_access(self):
        """Test auditor read-only access"""
        endpoints = [
            ("auditor/loans", "Get all loans"),
            ("auditor/payments", "Get all payments"),
            ("auditor/audit-logs", "Get audit logs")
        ]
        
        results = []
        for endpoint, name in endpoints:
            success, response = self.run_test(
                f"Auditor: {name}",
                "GET",
                endpoint,
                200,
                token=self.tokens.get('auditor')
            )
            results.append(success)
        
        return all(results)

    def test_role_based_permissions(self):
        """Test that roles cannot access unauthorized endpoints"""
        print("\n🔒 Testing Role-Based Access Control...")
        
        # Customer should not be able to approve loans
        success, _ = self.run_test(
            "Customer cannot approve loans",
            "POST",
            "officer/approve-loan",
            403,  # Expecting forbidden
            data={"entity_id": "dummy", "action": "approve"},
            token=self.tokens.get('customer')
        )
        
        # Collection agent should not access admin endpoints
        success2, _ = self.run_test(
            "Agent cannot access admin stats",
            "GET",
            "admin/stats",
            403,  # Expecting forbidden
            token=self.tokens.get('collection_agent')
        )
        
        return success and success2

def main():
    print("🚀 Starting SV Fincloud ERP System API Tests")
    print("=" * 60)
    
    tester = SVFincloudAPITester()
    
    # Test credentials from the request
    test_credentials = [
        ('admin', 'admin123', 'admin'),
        ('finance_officer', 'officer123', 'finance_officer'),
        ('collection_agent', 'agent123', 'collection_agent'),
        ('customer', 'customer123', 'customer'),
        ('auditor', 'auditor123', 'auditor')
    ]
    
    print("\n📋 Phase 1: Authentication Tests")
    print("-" * 40)
    
    # Test login for all roles
    login_success = True
    for username, password, role in test_credentials:
        if not tester.test_login(username, password, role):
            print(f"❌ Login failed for {role}, stopping tests")
            login_success = False
            break
        
        # Test /auth/me endpoint
        tester.test_auth_me(role)
    
    if not login_success:
        print(f"\n📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
        return 1
    
    print("\n📋 Phase 2: Customer Loan Applications")
    print("-" * 40)
    
    # Test loan applications
    loan_tests = [
        ("personal_loan", 50000, 12, {}),
        ("vehicle_loan", 100000, 24, {"vehicle_age": 2}),
        ("gold_loan", 30000, 6, {"gold_weight": 10})
    ]
    
    for loan_type, amount, tenure, extra_data in loan_tests:
        tester.test_customer_loan_application(loan_type, amount, tenure, **extra_data)
    
    # Get customer loans
    tester.test_get_customer_loans()
    
    print("\n📋 Phase 3: Finance Officer Operations")
    print("-" * 40)
    
    # Get pending applications
    tester.test_finance_officer_loan_applications()
    
    # Approve loans (if any were created)
    if tester.loan_ids:
        for i, loan_id in enumerate(tester.loan_ids[:2]):  # Approve first 2
            tester.test_approve_loan(loan_id, 'approve')
        
        # Reject remaining loans
        for loan_id in tester.loan_ids[2:]:
            tester.test_approve_loan(loan_id, 'reject')
        
        # Test EMI schedule generation
        if tester.loan_ids:
            tester.test_get_emi_schedule(tester.loan_ids[0])
    
    print("\n📋 Phase 4: Collection Agent Operations")
    print("-" * 40)
    
    # Get assigned customers
    success, customers = tester.test_collection_agent_customers()
    
    # Enter payment if EMI schedule exists
    if tester.loan_ids:
        success, emi_schedule = tester.test_get_emi_schedule(tester.loan_ids[0], 'collection_agent')
        if success and emi_schedule:
            first_emi = emi_schedule[0]
            tester.test_enter_payment(first_emi['id'], first_emi['emi_amount'])
    
    print("\n📋 Phase 5: Payment Approval")
    print("-" * 40)
    
    # Get pending payments
    tester.test_pending_payments()
    
    # Approve payments
    for payment_id in tester.payment_ids:
        tester.test_approve_payment(payment_id, 'approve')
    
    print("\n📋 Phase 6: Admin Operations")
    print("-" * 40)
    
    # Test admin dashboard
    tester.test_admin_stats()
    
    # Create new user
    tester.test_create_user(
        "test_customer", 
        "test123", 
        "customer",
        name="Test User",
        cibil_score=750
    )
    
    # Create branch
    tester.test_create_branch("SV Fincloud Delhi Branch", "Delhi")
    
    # Update rates
    tester.test_update_gold_rate(6800)
    tester.test_update_interest_rate("personal_loan", "cibil_750_plus", 11.5)
    
    print("\n📋 Phase 7: Auditor Operations")
    print("-" * 40)
    
    # Test auditor access
    tester.test_auditor_access()
    
    print("\n📋 Phase 8: Security Tests")
    print("-" * 40)
    
    # Test role-based permissions
    tester.test_role_based_permissions()
    
    # Test CIBIL-based rejection (create loan with low CIBIL)
    print("\n🔍 Testing CIBIL-based rejection...")
    # This would require creating a customer with low CIBIL first
    
    print("\n" + "=" * 60)
    print(f"📊 Final Results: {tester.tests_passed}/{tester.tests_run} tests passed")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print(f"⚠️  {tester.tests_run - tester.tests_passed} tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())