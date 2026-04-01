import requests
import sys
import json
from datetime import datetime

class AntigravityAPITester:
    def __init__(self, base_url="https://motion-studio-154.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.tests_run = 0
        self.tests_passed = 0
        self.user_token = None
        self.user_id = None
        self.project_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = self.session.headers.copy()
        if headers:
            test_headers.update(headers)

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = self.session.get(url, headers=test_headers)
            elif method == 'POST':
                response = self.session.post(url, json=data, headers=test_headers)
            elif method == 'PATCH':
                response = self.session.patch(url, json=data, headers=test_headers)
            elif method == 'DELETE':
                response = self.session.delete(url, headers=test_headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test API health endpoint"""
        return self.run_test("Health Check", "GET", "health", 200)

    def test_root_endpoint(self):
        """Test API root endpoint"""
        return self.run_test("Root Endpoint", "GET", "", 200)

    def test_skills_taxonomy(self):
        """Test skills taxonomy endpoint"""
        success, response = self.run_test("Skills Taxonomy", "GET", "users/skills/taxonomy", 200)
        if success and isinstance(response, dict):
            # Check if it has the expected structure
            expected_domains = ["engineering", "design", "business"]
            for domain in expected_domains:
                if domain not in response:
                    print(f"⚠️  Warning: Missing domain '{domain}' in taxonomy")
                    return False
            print(f"✅ Skills taxonomy has all expected domains")
        return success

    def test_user_registration(self):
        """Test user registration"""
        timestamp = datetime.now().strftime("%H%M%S")
        test_user = {
            "email": f"test_user_{timestamp}@example.com",
            "password": "TestPass123!",
            "full_name": f"Test User {timestamp}",
            "domain": "engineering"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=test_user
        )
        
        if success and isinstance(response, dict):
            if 'access_token' in response and 'id' in response:
                self.user_token = response['access_token']
                self.user_id = response['id']
                print(f"✅ Registration successful, got token and user ID")
                return True
            else:
                print(f"⚠️  Registration response missing token or ID")
        return False

    def test_user_login(self):
        """Test user login with provided credentials"""
        login_data = {
            "email": "test2@example.com",
            "password": "password123"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and isinstance(response, dict):
            if 'access_token' in response and 'id' in response:
                self.user_token = response['access_token']
                self.user_id = response['id']
                print(f"✅ Login successful, got token and user ID")
                return True
            else:
                print(f"⚠️  Login response missing token or ID")
        return False

    def test_get_current_user(self):
        """Test getting current user info"""
        if not self.user_token:
            print("❌ No user token available")
            return False
            
        headers = {"Authorization": f"Bearer {self.user_token}"}
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200,
            headers=headers
        )
        
        if success and isinstance(response, dict):
            if 'email' in response and 'domain' in response:
                print(f"✅ User info retrieved successfully")
                return True
        return False

    def test_create_project(self):
        """Test project creation"""
        if not self.user_token:
            print("❌ No user token available")
            return False
            
        project_data = {
            "title": f"Test Project {datetime.now().strftime('%H%M%S')}",
            "description": "A test project for API testing",
            "problem_statement": "Testing the project creation API",
            "target_market": "Students and developers",
            "industry_vertical": "Education",
            "stage": "ideation",
            "max_team_size": 4
        }
        
        headers = {"Authorization": f"Bearer {self.user_token}"}
        success, response = self.run_test(
            "Create Project",
            "POST",
            "projects",
            200,
            data=project_data,
            headers=headers
        )
        
        if success and isinstance(response, dict):
            if 'id' in response:
                self.project_id = response['id']
                print(f"✅ Project created successfully with ID: {self.project_id}")
                return True
        return False

    def test_list_projects(self):
        """Test listing projects"""
        if not self.user_token:
            print("❌ No user token available")
            return False
            
        headers = {"Authorization": f"Bearer {self.user_token}"}
        success, response = self.run_test(
            "List Projects",
            "GET",
            "projects",
            200,
            headers=headers
        )
        
        if success and isinstance(response, list):
            print(f"✅ Projects list retrieved successfully ({len(response)} projects)")
            return True
        return False

    def test_ai_idea_validation(self):
        """Test AI idea validation"""
        if not self.user_token:
            print("❌ No user token available")
            return False
            
        idea_data = {
            "title": "Smart Study Planner",
            "problem": "Students struggle to manage their study schedules effectively",
            "market": "University students worldwide",
            "industry": "Education Technology",
            "description": "An AI-powered app that creates personalized study schedules"
        }
        
        headers = {"Authorization": f"Bearer {self.user_token}"}
        success, response = self.run_test(
            "AI Idea Validation",
            "POST",
            "ai/validate",
            200,
            data=idea_data,
            headers=headers
        )
        
        if success and isinstance(response, dict):
            expected_fields = ["viability_score", "overall_grade", "verdict"]
            if all(field in response for field in expected_fields):
                print(f"✅ AI validation response has expected structure")
                return True
            else:
                print(f"⚠️  AI validation response missing expected fields")
        return False

    def test_project_matching(self):
        """Test project matching"""
        if not self.user_token:
            print("❌ No user token available")
            return False
            
        headers = {"Authorization": f"Bearer {self.user_token}"}
        success, response = self.run_test(
            "Project Matching",
            "GET",
            "match/projects",
            200,
            headers=headers
        )
        
        if success and isinstance(response, list):
            print(f"✅ Project matching retrieved successfully ({len(response)} matches)")
            return True
        return False

    def test_create_milestone(self):
        """Test milestone creation"""
        if not self.user_token or not self.project_id:
            print("❌ No user token or project ID available")
            return False
            
        milestone_data = {
            "title": "Test Milestone",
            "description": "A test milestone for API testing",
            "owner_domain": "engineering"
        }
        
        headers = {"Authorization": f"Bearer {self.user_token}"}
        success, response = self.run_test(
            "Create Milestone",
            "POST",
            f"projects/{self.project_id}/milestones",
            200,
            data=milestone_data,
            headers=headers
        )
        
        if success and isinstance(response, dict):
            if 'id' in response and 'title' in response:
                print(f"✅ Milestone created successfully")
                return True
        return False

    def test_skill_gap_analysis(self):
        """Test skill gap analysis"""
        if not self.user_token or not self.project_id:
            print("❌ No user token or project ID available")
            return False
            
        headers = {"Authorization": f"Bearer {self.user_token}"}
        success, response = self.run_test(
            "Skill Gap Analysis",
            "GET",
            f"ai/skill-gaps/{self.project_id}",
            200,
            headers=headers
        )
        
        if success and isinstance(response, dict):
            if 'coverage_percentage' in response and 'skills' in response:
                print(f"✅ Skill gap analysis completed successfully")
                return True
        return False

    def test_readiness_score(self):
        """Test startup readiness scoring"""
        if not self.user_token or not self.project_id:
            print("❌ No user token or project ID available")
            return False
            
        headers = {"Authorization": f"Bearer {self.user_token}"}
        success, response = self.run_test(
            "Readiness Score",
            "GET",
            f"ai/readiness/{self.project_id}",
            200,
            headers=headers
        )
        
        if success and isinstance(response, dict):
            if 'overall_score' in response and 'dimensions' in response:
                print(f"✅ Readiness score calculated successfully")
                return True
        return False

    def test_logout(self):
        """Test user logout"""
        success, response = self.run_test(
            "User Logout",
            "POST",
            "auth/logout",
            200
        )
        
        if success:
            self.user_token = None
            self.user_id = None
            print(f"✅ Logout successful")
            return True
        return False

def main():
    print("🚀 Starting Antigravity API Tests")
    print("=" * 50)
    
    tester = AntigravityAPITester()
    
    # Test sequence
    tests = [
        ("Health Check", tester.test_health_check),
        ("Root Endpoint", tester.test_root_endpoint),
        ("Skills Taxonomy", tester.test_skills_taxonomy),
        ("User Registration", tester.test_user_registration),
        ("User Login", tester.test_user_login),
        ("Get Current User", tester.test_get_current_user),
        ("Create Project", tester.test_create_project),
        ("List Projects", tester.test_list_projects),
        ("AI Idea Validation", tester.test_ai_idea_validation),
        ("Project Matching", tester.test_project_matching),
        ("Create Milestone", tester.test_create_milestone),
        ("Skill Gap Analysis", tester.test_skill_gap_analysis),
        ("Readiness Score", tester.test_readiness_score),
        ("User Logout", tester.test_logout),
    ]
    
    failed_tests = []
    
    for test_name, test_func in tests:
        try:
            success = test_func()
            if not success:
                failed_tests.append(test_name)
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
            failed_tests.append(test_name)
    
    # Print results
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {tester.tests_passed}/{tester.tests_run} passed")
    
    if failed_tests:
        print(f"\n❌ Failed tests:")
        for test in failed_tests:
            print(f"   - {test}")
        return 1
    else:
        print(f"\n✅ All tests passed!")
        return 0

if __name__ == "__main__":
    sys.exit(main())