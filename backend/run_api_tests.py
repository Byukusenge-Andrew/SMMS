#!/usr/bin/env python3
"""
Automated API Test Runner for SMMS
Run this script to test all major API endpoints
"""

import json
import os
import sys
import time
from datetime import datetime, timedelta

import django
import requests

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "social_media_manager.settings")
django.setup()


class SMSAPITester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.access_token = None
        self.refresh_token = None
        self.test_user_id = None
        self.test_post_id = None
        self.results = []

    def log_result(self, test_name, status, details=""):
        """Log test result"""
        result = {"test": test_name, "status": status, "details": details, "timestamp": datetime.now().isoformat()}
        self.results.append(result)

        status_icon = "✅" if status == "PASS" else "❌" if status == "FAIL" else "⚠️"
        print(f"{status_icon} {test_name}: {status}")
        if details:
            print(f"    {details}")

    def make_request(self, method, endpoint, data=None, headers=None, auth=True):
        """Make HTTP request with optional authentication"""
        url = f"{self.base_url}{endpoint}"

        if headers is None:
            headers = {"Content-Type": "application/json"}

        if auth and self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=data)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"Unsupported method: {method}")

            return response
        except Exception as e:
            return None

    def test_user_registration(self):
        """Test user registration"""
        test_data = {
            "username": f"testuser_{int(time.time())}",
            "email": f"test_{int(time.time())}@example.com",
            "password": "TestPassword123!",
            "password2": "TestPassword123!",
            "first_name": "Test",
            "last_name": "User",
        }

        response = self.make_request("POST", "/api/auth/register/", test_data, auth=False)

        if response and response.status_code == 201:
            data = response.json()
            self.access_token = data.get("access")
            self.refresh_token = data.get("refresh")
            self.test_user_id = data.get("user", {}).get("id")
            self.log_result("User Registration", "PASS", f"User ID: {self.test_user_id}")
        else:
            error = response.json() if response else "No response"
            self.log_result(
                "User Registration", "FAIL", f"Status: {response.status_code if response else 'N/A'}, Error: {error}"
            )

    def test_user_login(self):
        """Test user login (if registration failed)"""
        if self.access_token:
            return  # Already have token from registration

        test_data = {"username": "admin", "password": "admin123"}  # Assuming admin user exists

        response = self.make_request("POST", "/api/auth/login/", test_data, auth=False)

        if response and response.status_code == 200:
            data = response.json()
            self.access_token = data.get("access")
            self.refresh_token = data.get("refresh")
            self.log_result("User Login", "PASS")
        else:
            self.log_result("User Login", "FAIL", f"Status: {response.status_code if response else 'N/A'}")

    def test_user_profile(self):
        """Test getting user profile"""
        response = self.make_request("GET", "/api/auth/profile/")

        if response and response.status_code == 200:
            self.log_result("User Profile", "PASS")
        else:
            self.log_result("User Profile", "FAIL", f"Status: {response.status_code if response else 'N/A'}")

    def test_create_post(self):
        """Test creating a new post"""
        test_data = {
            "title": "API Test Post",
            "content": "This is a test post created by the API tester",
            "platforms": ["twitter"],
            "status": "draft",
        }

        response = self.make_request("POST", "/api/posts/", test_data)

        if response and response.status_code == 201:
            data = response.json()
            self.test_post_id = data.get("id")
            self.log_result("Create Post", "PASS", f"Post ID: {self.test_post_id}")
        else:
            error = response.json() if response else "No response"
            self.log_result("Create Post", "FAIL", f"Status: {response.status_code if response else 'N/A'}, Error: {error}")

    def test_list_posts(self):
        """Test listing posts"""
        response = self.make_request("GET", "/api/posts/")

        if response and response.status_code == 200:
            data = response.json()
            count = (
                len(data.get("results", data))
                if isinstance(data, dict) and "results" in data
                else len(data) if isinstance(data, list) else 0
            )
            self.log_result("List Posts", "PASS", f"Found {count} posts")
        else:
            self.log_result("List Posts", "FAIL", f"Status: {response.status_code if response else 'N/A'}")

    def test_get_post_detail(self):
        """Test getting post details"""
        if not self.test_post_id:
            self.log_result("Get Post Detail", "SKIP", "No test post ID available")
            return

        response = self.make_request("GET", f"/api/posts/{self.test_post_id}/")

        if response and response.status_code == 200:
            self.log_result("Get Post Detail", "PASS")
        else:
            self.log_result("Get Post Detail", "FAIL", f"Status: {response.status_code if response else 'N/A'}")

    def test_ai_content_suggestions(self):
        """Test AI content suggestions"""
        test_data = {"platform": "twitter", "topic": "technology"}

        response = self.make_request("POST", "/api/posts/ai/content-suggestions/", test_data)

        if response and response.status_code == 200:
            data = response.json()
            suggestions_count = len(data.get("suggestions", []))
            self.log_result("AI Content Suggestions", "PASS", f"Generated {suggestions_count} suggestions")
        else:
            error = response.json() if response else "No response"
            self.log_result(
                "AI Content Suggestions", "FAIL", f"Status: {response.status_code if response else 'N/A'}, Error: {error}"
            )

    def test_sentiment_analysis(self):
        """Test sentiment analysis"""
        test_data = {"comment": "This is absolutely amazing! I love it so much! 😍"}

        response = self.make_request("POST", "/api/posts/ai/sentiment/comment/", test_data)

        if response and response.status_code == 200:
            data = response.json()
            sentiment = data.get("sentiment", "unknown")
            confidence = data.get("confidence", 0)
            self.log_result("Sentiment Analysis", "PASS", f"Sentiment: {sentiment}, Confidence: {confidence}")
        else:
            error = response.json() if response else "No response"
            self.log_result(
                "Sentiment Analysis", "FAIL", f"Status: {response.status_code if response else 'N/A'}, Error: {error}"
            )

    def test_bulk_sentiment_analysis(self):
        """Test bulk sentiment analysis"""
        if not self.test_post_id:
            self.log_result("Bulk Sentiment Analysis", "SKIP", "No test post ID available")
            return

        test_data = {"comments": ["This is amazing!", "Great work!", "Could be better", "Not impressed"]}

        response = self.make_request("POST", f"/api/posts/ai/sentiment/post/{self.test_post_id}/", test_data)

        if response and response.status_code == 200:
            data = response.json()
            overall_sentiment = data.get("overall_sentiment", "unknown")
            comments_analyzed = data.get("comments_analyzed", 0)
            self.log_result("Bulk Sentiment Analysis", "PASS", f"Overall: {overall_sentiment}, Comments: {comments_analyzed}")
        else:
            error = response.json() if response else "No response"
            self.log_result(
                "Bulk Sentiment Analysis", "FAIL", f"Status: {response.status_code if response else 'N/A'}, Error: {error}"
            )

    def test_analytics_data(self):
        """Test analytics data endpoint"""
        params = {
            "start_date": (datetime.now() - timedelta(days=30)).date().isoformat(),
            "end_date": datetime.now().date().isoformat(),
        }

        response = self.make_request("GET", "/api/analytics/data/", params)

        if response and response.status_code == 200:
            self.log_result("Analytics Data", "PASS")
        else:
            self.log_result("Analytics Data", "FAIL", f"Status: {response.status_code if response else 'N/A'}")

    def test_ai_insights(self):
        """Test AI insights"""
        test_data = {"period": "last_30_days"}

        response = self.make_request("POST", "/api/analytics/ai-insights/", test_data)

        if response and response.status_code == 200:
            data = response.json()
            insights_count = len(data.get("insights", []))
            self.log_result("AI Insights", "PASS", f"Generated {insights_count} insights")
        else:
            error = response.json() if response else "No response"
            self.log_result("AI Insights", "FAIL", f"Status: {response.status_code if response else 'N/A'}, Error: {error}")

    def test_notifications(self):
        """Test notifications endpoint"""
        response = self.make_request("GET", "/api/notifications/")

        if response and response.status_code == 200:
            data = response.json()
            count = (
                len(data.get("results", data))
                if isinstance(data, dict) and "results" in data
                else len(data) if isinstance(data, list) else 0
            )
            self.log_result("Notifications", "PASS", f"Found {count} notifications")
        else:
            self.log_result("Notifications", "FAIL", f"Status: {response.status_code if response else 'N/A'}")

    def test_collaborators(self):
        """Test collaborators endpoint"""
        response = self.make_request("GET", "/api/collaborators/")

        if response and response.status_code == 200:
            data = response.json()
            count = (
                len(data.get("results", data))
                if isinstance(data, dict) and "results" in data
                else len(data) if isinstance(data, list) else 0
            )
            self.log_result("Collaborators", "PASS", f"Found {count} collaborators")
        else:
            self.log_result("Collaborators", "FAIL", f"Status: {response.status_code if response else 'N/A'}")

    def cleanup(self):
        """Clean up test data"""
        if self.test_post_id:
            response = self.make_request("DELETE", f"/api/posts/{self.test_post_id}/")
            if response and response.status_code == 204:
                self.log_result("Cleanup - Delete Test Post", "PASS")
            else:
                self.log_result("Cleanup - Delete Test Post", "FAIL")

    def run_all_tests(self):
        """Run all API tests"""
        print("🚀 Starting SMMS API Tests")
        print("=" * 50)

        # Authentication tests
        print("\n📝 Authentication Tests")
        self.test_user_registration()
        self.test_user_login()
        self.test_user_profile()

        # Posts tests
        print("\n📄 Posts Tests")
        self.test_create_post()
        self.test_list_posts()
        self.test_get_post_detail()

        # AI features tests
        print("\n🤖 AI Features Tests")
        self.test_ai_content_suggestions()
        self.test_sentiment_analysis()
        self.test_bulk_sentiment_analysis()

        # Analytics tests
        print("\n📊 Analytics Tests")
        self.test_analytics_data()
        self.test_ai_insights()

        # Other features tests
        print("\n🔔 Other Features Tests")
        self.test_notifications()
        self.test_collaborators()

        # Cleanup
        print("\n🧹 Cleanup")
        self.cleanup()

        # Summary
        self.print_summary()

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)

        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["status"] == "PASS"])
        failed_tests = len([r for r in self.results if r["status"] == "FAIL"])
        skipped_tests = len([r for r in self.results if r["status"] == "SKIP"])

        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"⚠️ Skipped: {skipped_tests}")

        success_rate = (passed_tests / (total_tests - skipped_tests) * 100) if (total_tests - skipped_tests) > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")

        if failed_tests > 0:
            print("\n❌ Failed Tests:")
            for result in self.results:
                if result["status"] == "FAIL":
                    print(f"  - {result['test']}: {result['details']}")

        # Save results to file
        with open("api_test_results.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n💾 Results saved to api_test_results.json")


if __name__ == "__main__":
    tester = SMSAPITester()
    tester.run_all_tests()
