from fastapi import FastAPI, APIRouter, HTTPException, Request, Depends
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timedelta
import requests
import hashlib
import hmac
import json
from passlib.context import CryptContext
from jose import JWTError, jwt
import bcrypt

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Xendit Configuration
XENDIT_SECRET_KEY = os.environ.get('XENDIT_SECRET_KEY', 'xnd_development_USTCXnjTj7rFxHbxMLzscFKTNWymiHUhCP8jSFJXfCxXHKp0co9zGMWwQ3jgWN')
XENDIT_PUBLIC_KEY = os.environ.get('XENDIT_PUBLIC_KEY', 'xnd_public_development_KJsG5179pG4LxZHHRQXGED8GVJoQLqBjkZm2kRJIPyW6zZEYmoeRowzqSUgY')
XENDIT_WEBHOOK_TOKEN = os.environ.get('XENDIT_WEBHOOK_TOKEN', 'NotoAOU6dRX8gCSy5Gc1bP4UHhHsjBhrHJqxSFPopvDTMdYW')

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-here')
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Create the main app without a prefix
app = FastAPI(title="E-commerce API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    email: EmailStr
    hashed_password: str
    role: str = "customer"
    address: Optional[str] = None
    phone: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    address: Optional[str] = None
    phone: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Product(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    price: float
    stock: int
    category: str
    images: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ProductCreate(BaseModel):
    name: str
    description: str
    price: float
    stock: int
    category: str
    images: List[str] = []

class CartItem(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    product_id: str
    quantity: int
    price: float
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CartItemCreate(BaseModel):
    product_id: str
    quantity: int

class Order(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    user_email: str
    items: List[Dict[str, Any]] = []
    total_amount: float
    status: str = "pending"
    payment_method: str
    xendit_invoice_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class OrderCreate(BaseModel):
    user_email: str
    payment_method: str = "CREDIT_CARD"

class PaymentTransaction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    order_id: str
    user_id: Optional[str] = None
    amount: float
    currency: str = "IDR"
    status: str = "pending"
    payment_method: str
    xendit_invoice_id: Optional[str] = None
    xendit_payment_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class SubscriptionPlan(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    price: float
    billing_cycle: str = "monthly"  # monthly, yearly
    features: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Subscription(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    plan_id: str
    status: str = "active"
    start_date: datetime = Field(default_factory=datetime.utcnow)
    end_date: Optional[datetime] = None
    xendit_subscription_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(lambda: None)):
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
        user = await db.users.find_one({"id": user_id})
        return User(**user) if user else None
    except JWTError:
        return None

# Authentication Routes
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        name=user_data.name,
        email=user_data.email,
        hashed_password=hashed_password,
        address=user_data.address,
        phone=user_data.phone
    )
    
    await db.users.insert_one(user.dict())
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }

@api_router.post("/auth/login")
async def login(user_data: UserLogin):
    user = await db.users.find_one({"email": user_data.email})
    if not user or not verify_password(user_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["id"]}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
    }

# Product Routes
@api_router.get("/products", response_model=List[Product])
async def get_products(category: Optional[str] = None, limit: int = 20, skip: int = 0):
    query = {}
    if category:
        query["category"] = category
    
    products = await db.products.find(query).skip(skip).limit(limit).to_list(limit)
    return [Product(**product) for product in products]

@api_router.get("/products/{product_id}", response_model=Product)
async def get_product(product_id: str):
    product = await db.products.find_one({"id": product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**product)

@api_router.post("/products", response_model=Product)
async def create_product(product_data: ProductCreate):
    product = Product(**product_data.dict())
    await db.products.insert_one(product.dict())
    return product

# Cart Routes
@api_router.post("/cart/add")
async def add_to_cart(item_data: CartItemCreate, session_id: Optional[str] = None, user_id: Optional[str] = None):
    # Get product details
    product = await db.products.find_one({"id": item_data.product_id})
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    if product["stock"] < item_data.quantity:
        raise HTTPException(status_code=400, detail="Insufficient stock")
    
    # Check if item already in cart
    query = {"product_id": item_data.product_id}
    if user_id:
        query["user_id"] = user_id
    else:
        query["session_id"] = session_id or str(uuid.uuid4())
    
    existing_item = await db.cart_items.find_one(query)
    
    if existing_item:
        # Update quantity
        new_quantity = existing_item["quantity"] + item_data.quantity
        await db.cart_items.update_one(
            {"id": existing_item["id"]},
            {"$set": {"quantity": new_quantity}}
        )
    else:
        # Create new cart item
        cart_item = CartItem(
            user_id=user_id,
            session_id=session_id or str(uuid.uuid4()),
            product_id=item_data.product_id,
            quantity=item_data.quantity,
            price=product["price"]
        )
        await db.cart_items.insert_one(cart_item.dict())
    
    return {"message": "Item added to cart"}

@api_router.get("/cart")
async def get_cart(session_id: Optional[str] = None, user_id: Optional[str] = None):
    query = {}
    if user_id:
        query["user_id"] = user_id
    elif session_id:
        query["session_id"] = session_id
    else:
        return {"items": [], "total": 0}
    
    cart_items = await db.cart_items.find(query).to_list(100)
    
    # Get product details for each item
    items_with_products = []
    total = 0
    
    for item in cart_items:
        product = await db.products.find_one({"id": item["product_id"]})
        if product:
            item_total = item["quantity"] * item["price"]
            total += item_total
            items_with_products.append({
                "id": item["id"],
                "product": product,
                "quantity": item["quantity"],
                "price": item["price"],
                "total": item_total
            })
    
    return {"items": items_with_products, "total": total}

@api_router.delete("/cart/{item_id}")
async def remove_from_cart(item_id: str):
    result = await db.cart_items.delete_one({"id": item_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Cart item not found")
    return {"message": "Item removed from cart"}

# Order and Payment Routes
@api_router.post("/orders/create")
async def create_order(order_data: OrderCreate, session_id: Optional[str] = None, user_id: Optional[str] = None):
    # Get cart items
    query = {}
    if user_id:
        query["user_id"] = user_id
    elif session_id:
        query["session_id"] = session_id
    else:
        raise HTTPException(status_code=400, detail="No cart found")
    
    cart_items = await db.cart_items.find(query).to_list(100)
    if not cart_items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    
    # Calculate total and prepare order items
    total_amount = 0
    order_items = []
    
    for item in cart_items:
        product = await db.products.find_one({"id": item["product_id"]})
        if product:
            item_total = item["quantity"] * item["price"]
            total_amount += item_total
            order_items.append({
                "product_id": item["product_id"],
                "product_name": product["name"],
                "quantity": item["quantity"],
                "price": item["price"],
                "total": item_total
            })
    
    # Create order
    order = Order(
        user_id=user_id,
        user_email=order_data.user_email,
        items=order_items,
        total_amount=total_amount,
        payment_method=order_data.payment_method
    )
    
    await db.orders.insert_one(order.dict())
    
    # Create Xendit invoice
    try:
        headers = {
            "Authorization": f"Basic {XENDIT_SECRET_KEY}:",
            "Content-Type": "application/json"
        }
        
        invoice_data = {
            "external_id": f"order_{order.id}",
            "amount": total_amount,
            "payer_email": order_data.user_email,
            "description": f"Order #{order.id[:8]}",
            "currency": "IDR",
            "payment_methods": ["CREDIT_CARD", "BANK_TRANSFER", "QRIS", "EWALLET"]
        }
        
        response = requests.post(
            "https://api.xendit.co/v2/invoices",
            headers=headers,
            json=invoice_data
        )
        
        if response.status_code == 200:
            invoice = response.json()
            
            # Update order with Xendit invoice ID
            await db.orders.update_one(
                {"id": order.id},
                {"$set": {"xendit_invoice_id": invoice["id"]}}
            )
            
            # Create payment transaction record
            payment_transaction = PaymentTransaction(
                order_id=order.id,
                user_id=user_id,
                amount=total_amount,
                payment_method=order_data.payment_method,
                xendit_invoice_id=invoice["id"]
            )
            await db.payment_transactions.insert_one(payment_transaction.dict())
            
            # Clear cart
            await db.cart_items.delete_many(query)
            
            return {
                "order_id": order.id,
                "payment_url": invoice["invoice_url"],
                "total_amount": total_amount
            }
        else:
            raise HTTPException(status_code=400, detail="Failed to create payment")
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment creation failed: {str(e)}")

@api_router.get("/orders/{order_id}")
async def get_order(order_id: str):
    order = await db.orders.find_one({"id": order_id})
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return Order(**order)

@api_router.get("/orders")
async def get_orders(user_id: Optional[str] = None, limit: int = 20, skip: int = 0):
    query = {}
    if user_id:
        query["user_id"] = user_id
    
    orders = await db.orders.find(query).skip(skip).limit(limit).to_list(limit)
    return [Order(**order) for order in orders]

# Webhook handler for Xendit
@api_router.post("/webhook/xendit")
async def xendit_webhook(request: Request):
    try:
        body = await request.body()
        signature = request.headers.get("x-callback-token")
        
        # Verify webhook signature
        if signature != XENDIT_WEBHOOK_TOKEN:
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        
        data = json.loads(body)
        
        # Handle invoice status updates
        if "external_id" in data and data["external_id"].startswith("order_"):
            order_id = data["external_id"].replace("order_", "")
            
            # Update order status
            status_mapping = {
                "PAID": "completed",
                "EXPIRED": "cancelled",
                "SETTLED": "completed"
            }
            
            new_status = status_mapping.get(data.get("status"), "pending")
            
            await db.orders.update_one(
                {"id": order_id},
                {"$set": {"status": new_status, "updated_at": datetime.utcnow()}}
            )
            
            # Update payment transaction
            await db.payment_transactions.update_one(
                {"order_id": order_id},
                {"$set": {
                    "status": new_status,
                    "xendit_payment_id": data.get("payment_id"),
                    "updated_at": datetime.utcnow()
                }}
            )
        
        return {"status": "success"}
    
    except Exception as e:
        logging.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

# Subscription Routes
@api_router.get("/subscription-plans", response_model=List[SubscriptionPlan])
async def get_subscription_plans():
    plans = await db.subscription_plans.find().to_list(100)
    return [SubscriptionPlan(**plan) for plan in plans]

@api_router.post("/subscription-plans", response_model=SubscriptionPlan)
async def create_subscription_plan(plan_data: SubscriptionPlan):
    await db.subscription_plans.insert_one(plan_data.dict())
    return plan_data

# Initialize sample data
@api_router.post("/admin/init-data")
async def initialize_sample_data():
    # Check if data already exists
    product_count = await db.products.count_documents({})
    if product_count > 0:
        return {"message": "Sample data already exists"}
    
    # Sample products
    sample_products = [
        {
            "id": str(uuid.uuid4()),
            "name": "Premium Subscription (Monthly)",
            "description": "Get access to all premium features with monthly billing",
            "price": 99000.0,
            "stock": 1000,
            "category": "subscription",
            "images": ["https://images.pexels.com/photos/7563569/pexels-photo-7563569.jpeg"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Basic Package",
            "description": "Essential features for getting started",
            "price": 49000.0,
            "stock": 1000,
            "category": "package",
            "images": ["https://images.pexels.com/photos/6995253/pexels-photo-6995253.jpeg"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Pro Package",
            "description": "Advanced features for power users",
            "price": 149000.0,
            "stock": 1000,
            "category": "package",
            "images": ["https://images.pexels.com/photos/9169180/pexels-photo-9169180.jpeg"],
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    ]
    
    await db.products.insert_many(sample_products)
    
    # Sample subscription plans
    sample_plans = [
        {
            "id": str(uuid.uuid4()),
            "name": "Basic Plan",
            "description": "Perfect for individuals",
            "price": 79000.0,
            "billing_cycle": "monthly",
            "features": ["Basic Features", "Email Support", "5GB Storage"],
            "created_at": datetime.utcnow()
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Pro Plan",
            "description": "Great for small teams",
            "price": 199000.0,
            "billing_cycle": "monthly",
            "features": ["All Basic Features", "Priority Support", "50GB Storage", "Advanced Analytics"],
            "created_at": datetime.utcnow()
        }
    ]
    
    await db.subscription_plans.insert_many(sample_plans)
    
    return {"message": "Sample data initialized successfully"}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()