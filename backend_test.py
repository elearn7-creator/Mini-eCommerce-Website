import requests
import json
import time
import random
import string
import os
from dotenv import load_dotenv
import sys

# Load environment variables from frontend .env file to get the backend URL
load_dotenv('/app/frontend/.env')

# Get the backend URL from environment variables
BACKEND_URL = os.environ.get('REACT_APP_BACKEND_URL')
if not BACKEND_URL:
    print("Error: REACT_APP_BACKEND_URL not found in environment variables")
    sys.exit(1)

API_URL = f"{BACKEND_URL}/api"
print(f"Using API URL: {API_URL}")

# Test results tracking
test_results = {
    "passed": 0,
    "failed": 0,
    "tests": []
}

# Helper function to generate random email
def generate_random_email():
    random_string = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{random_string}@example.com"

# Helper function to record test results
def record_test(name, passed, message=None, response=None):
    status = "PASSED" if passed else "FAILED"
    test_results["tests"].append({
        "name": name,
        "status": status,
        "message": message
    })
    
    if passed:
        test_results["passed"] += 1
        print(f"✅ {name}: {status}")
    else:
        test_results["failed"] += 1
        print(f"❌ {name}: {status}")
        if message:
            print(f"   Message: {message}")
        if response:
            try:
                print(f"   Response: {response.status_code} - {response.json()}")
            except:
                print(f"   Response: {response.status_code} - {response.text}")

# 1. Test User Registration
def test_user_registration():
    print("\n=== Testing User Registration ===")
    
    # Generate random user data
    email = generate_random_email()
    user_data = {
        "name": "Test User",
        "email": email,
        "password": "Password123!",
        "address": "123 Test Street",
        "phone": "1234567890"
    }
    
    # Make the request
    response = requests.post(f"{API_URL}/auth/register", json=user_data)
    
    # Check if registration was successful
    if response.status_code == 200:
        data = response.json()
        record_test("User Registration", True, f"User registered with email: {email}")
        return data.get("access_token"), data.get("user", {}).get("id"), email
    else:
        record_test("User Registration", False, "Failed to register user", response)
        return None, None, email

# 2. Test User Login
def test_user_login(email, password="Password123!"):
    print("\n=== Testing User Login ===")
    
    login_data = {
        "email": email,
        "password": password
    }
    
    # Make the request
    response = requests.post(f"{API_URL}/auth/login", json=login_data)
    
    # Check if login was successful
    if response.status_code == 200:
        data = response.json()
        record_test("User Login", True, f"User logged in with email: {email}")
        return data.get("access_token"), data.get("user", {}).get("id")
    else:
        record_test("User Login", False, "Failed to login", response)
        return None, None

# 3. Test Initialize Sample Data
def test_init_data():
    print("\n=== Testing Initialize Sample Data ===")
    
    # Make the request
    response = requests.post(f"{API_URL}/admin/init-data")
    
    # Check if initialization was successful
    if response.status_code == 200:
        record_test("Initialize Sample Data", True, "Sample data initialized successfully")
        return True
    else:
        # If data already exists, that's also a success
        if response.status_code == 200 and "already exists" in response.text:
            record_test("Initialize Sample Data", True, "Sample data already exists")
            return True
        record_test("Initialize Sample Data", False, "Failed to initialize sample data", response)
        return False

# 4. Test Get Products
def test_get_products():
    print("\n=== Testing Get Products ===")
    
    # Make the request
    response = requests.get(f"{API_URL}/products")
    
    # Check if products were retrieved successfully
    if response.status_code == 200:
        products = response.json()
        if len(products) > 0:
            record_test("Get Products", True, f"Retrieved {len(products)} products")
            return products
        else:
            record_test("Get Products", False, "No products found", response)
            return []
    else:
        record_test("Get Products", False, "Failed to get products", response)
        return []

# 5. Test Add to Cart
def test_add_to_cart(product_id, session_id=None, user_id=None):
    print("\n=== Testing Add to Cart ===")
    
    cart_data = {
        "product_id": product_id,
        "quantity": 1
    }
    
    params = {}
    if session_id:
        params["session_id"] = session_id
    if user_id:
        params["user_id"] = user_id
    
    # Make the request
    response = requests.post(f"{API_URL}/cart/add", json=cart_data, params=params)
    
    # Check if item was added to cart successfully
    if response.status_code == 200:
        record_test("Add to Cart", True, f"Added product {product_id} to cart")
        return True
    else:
        record_test("Add to Cart", False, "Failed to add item to cart", response)
        return False

# 6. Test Get Cart
def test_get_cart(session_id=None, user_id=None):
    print("\n=== Testing Get Cart ===")
    
    params = {}
    if session_id:
        params["session_id"] = session_id
    if user_id:
        params["user_id"] = user_id
    
    # Make the request
    response = requests.get(f"{API_URL}/cart", params=params)
    
    # Check if cart was retrieved successfully
    if response.status_code == 200:
        cart = response.json()
        record_test("Get Cart", True, f"Retrieved cart with {len(cart.get('items', []))} items")
        return cart
    elif response.status_code == 500:
        # This is a known issue with MongoDB ObjectId serialization
        record_test("Get Cart", False, "Failed to get cart due to MongoDB ObjectId serialization issue", response)
        return None
    else:
        record_test("Get Cart", False, "Failed to get cart", response)
        return None

# 7. Test Remove from Cart
def test_remove_from_cart(item_id):
    print("\n=== Testing Remove from Cart ===")
    
    # Make the request
    response = requests.delete(f"{API_URL}/cart/{item_id}")
    
    # Check if item was removed from cart successfully
    if response.status_code == 200:
        record_test("Remove from Cart", True, f"Removed item {item_id} from cart")
        return True
    else:
        record_test("Remove from Cart", False, "Failed to remove item from cart", response)
        return False

# 8. Test Create Order
def test_create_order(email, session_id=None, user_id=None):
    print("\n=== Testing Create Order ===")
    
    order_data = {
        "user_email": email,
        "payment_method": "CREDIT_CARD"
    }
    
    params = {}
    if session_id:
        params["session_id"] = session_id
    if user_id:
        params["user_id"] = user_id
    
    # Make the request
    response = requests.post(f"{API_URL}/orders/create", json=order_data, params=params)
    
    # Check if order was created successfully
    if response.status_code == 200:
        order = response.json()
        record_test("Create Order", True, f"Created order with ID: {order.get('order_id')}")
        return order
    elif response.status_code == 500 and "Payment creation failed" in response.text:
        # This is likely due to Xendit API issues in test environment
        record_test("Create Order", False, "Failed to create order due to Xendit payment integration issues", response)
        return None
    else:
        record_test("Create Order", False, "Failed to create order", response)
        return None

# 9. Test Get Subscription Plans
def test_get_subscription_plans():
    print("\n=== Testing Get Subscription Plans ===")
    
    # Make the request
    response = requests.get(f"{API_URL}/subscription-plans")
    
    # Check if subscription plans were retrieved successfully
    if response.status_code == 200:
        plans = response.json()
        if len(plans) > 0:
            record_test("Get Subscription Plans", True, f"Retrieved {len(plans)} subscription plans")
            return plans
        else:
            record_test("Get Subscription Plans", False, "No subscription plans found", response)
            return []
    else:
        record_test("Get Subscription Plans", False, "Failed to get subscription plans", response)
        return []

# Main test function
def run_tests():
    print("\n========== STARTING E-COMMERCE BACKEND TESTS ==========\n")
    
    # Initialize sample data
    init_success = test_init_data()
    if not init_success:
        print("Failed to initialize sample data. Some tests may fail.")
    
    # Get products to use in tests
    products = test_get_products()
    if not products:
        print("No products found. Some tests may fail.")
        return
    
    # Select a product for cart tests
    product_id = products[0]["id"] if products else None
    if not product_id:
        print("No product ID available. Cart and order tests will be skipped.")
        return
    
    # Register a new user
    token, user_id, email = test_user_registration()
    
    # If registration failed, try login with a predefined user
    if not token:
        print("Registration failed. Trying to login with a predefined user.")
        email = "test@example.com"
        token, user_id = test_user_login(email)
    
    # Generate a session ID for non-authenticated tests
    session_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=32))
    
    # Test cart functionality
    if product_id:
        # Add item to cart
        add_success = test_add_to_cart(product_id, session_id, user_id)
        
        # Get cart
        cart = test_get_cart(session_id, user_id)
        
        # Test remove from cart if there are items
        if cart and cart.get("items"):
            item_id = cart["items"][0]["id"]
            test_remove_from_cart(item_id)
        
        # Add item back to cart for order test
        if add_success:
            test_add_to_cart(product_id, session_id, user_id)
        
        # Create order
        if email:
            test_create_order(email, session_id, user_id)
    
    # Test subscription plans
    test_get_subscription_plans()
    
    # Print summary
    print("\n========== TEST SUMMARY ==========")
    print(f"Total tests: {test_results['passed'] + test_results['failed']}")
    print(f"Passed: {test_results['passed']}")
    print(f"Failed: {test_results['failed']}")
    
    # Return overall success
    return test_results["failed"] == 0

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)