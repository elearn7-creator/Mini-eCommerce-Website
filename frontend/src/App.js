import React, { useState, useEffect, createContext, useContext } from "react";
import "./App.css";
import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Context for authentication and cart
const AppContext = createContext();

const useAppContext = () => {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within AppProvider');
  }
  return context;
};

// Context Provider
const AppProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [cart, setCart] = useState({ items: [], total: 0 });
  const [sessionId] = useState(() => localStorage.getItem('sessionId') || (() => {
    const id = Date.now().toString();
    localStorage.setItem('sessionId', id);
    return id;
  })());

  const fetchCart = async () => {
    try {
      const response = await axios.get(`${API}/cart?session_id=${sessionId}`);
      setCart(response.data);
    } catch (error) {
      console.error('Error fetching cart:', error);
    }
  };

  const addToCart = async (productId, quantity = 1) => {
    try {
      await axios.post(`${API}/cart/add?session_id=${sessionId}`, {
        product_id: productId,
        quantity: quantity
      });
      fetchCart();
    } catch (error) {
      console.error('Error adding to cart:', error);
      alert('Failed to add item to cart');
    }
  };

  const removeFromCart = async (itemId) => {
    try {
      await axios.delete(`${API}/cart/${itemId}`);
      fetchCart();
    } catch (error) {
      console.error('Error removing from cart:', error);
    }
  };

  useEffect(() => {
    fetchCart();
  }, []);

  return (
    <AppContext.Provider value={{
      user,
      setUser,
      cart,
      sessionId,
      addToCart,
      removeFromCart,
      fetchCart
    }}>
      {children}
    </AppContext.Provider>
  );
};

// Components
const Header = () => {
  const { cart, user, setUser } = useAppContext();
  const [showCart, setShowCart] = useState(false);

  const logout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  return (
    <header className="bg-white shadow-lg sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center py-4">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-blue-600">ShopINA</h1>
            <span className="ml-2 text-sm text-gray-500">Indonesian E-commerce</span>
          </div>
          
          <nav className="hidden md:flex space-x-8">
            <a href="#home" className="text-gray-700 hover:text-blue-600">Home</a>
            <a href="#products" className="text-gray-700 hover:text-blue-600">Products</a>
            <a href="#subscriptions" className="text-gray-700 hover:text-blue-600">Subscriptions</a>
          </nav>

          <div className="flex items-center space-x-4">
            {user ? (
              <div className="flex items-center space-x-4">
                <span className="text-gray-700">Hello, {user.name}</span>
                <button onClick={logout} className="text-red-600 hover:text-red-800">
                  Logout
                </button>
              </div>
            ) : (
              <AuthModal />
            )}
            
            <button
              onClick={() => setShowCart(!showCart)}
              className="relative bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
            >
              Cart ({cart.items.length})
              {cart.items.length > 0 && (
                <span className="absolute -top-2 -right-2 bg-red-500 text-white rounded-full w-5 h-5 flex items-center justify-center text-xs">
                  {cart.items.length}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
      
      {showCart && <CartDropdown onClose={() => setShowCart(false)} />}
    </header>
  );
};

const AuthModal = () => {
  const [showModal, setShowModal] = useState(false);
  const [isLogin, setIsLogin] = useState(true);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    password: '',
    address: '',
    phone: ''
  });
  const { setUser } = useAppContext();

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    try {
      const endpoint = isLogin ? '/auth/login' : '/auth/register';
      const payload = isLogin ? 
        { email: formData.email, password: formData.password } :
        formData;
      
      const response = await axios.post(`${API}${endpoint}`, payload);
      
      localStorage.setItem('token', response.data.access_token);
      setUser(response.data.user);
      setShowModal(false);
      setFormData({ name: '', email: '', password: '', address: '', phone: '' });
    } catch (error) {
      alert(error.response?.data?.detail || 'Authentication failed');
    }
  };

  if (!showModal) {
    return (
      <button
        onClick={() => setShowModal(true)}
        className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
      >
        Login / Register
      </button>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-bold">{isLogin ? 'Login' : 'Register'}</h2>
          <button onClick={() => setShowModal(false)} className="text-gray-500 hover:text-gray-700">
            ✕
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          {!isLogin && (
            <>
              <input
                type="text"
                placeholder="Full Name"
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
              />
              <input
                type="text"
                placeholder="Address"
                value={formData.address}
                onChange={(e) => setFormData({...formData, address: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="tel"
                placeholder="Phone Number"
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </>
          )}
          
          <input
            type="email"
            placeholder="Email"
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          
          <input
            type="password"
            placeholder="Password"
            value={formData.password}
            onChange={(e) => setFormData({...formData, password: e.target.value})}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            required
          />
          
          <button
            type="submit"
            className="w-full bg-blue-600 text-white py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            {isLogin ? 'Login' : 'Register'}
          </button>
        </form>
        
        <p className="mt-4 text-center text-sm text-gray-600">
          {isLogin ? "Don't have an account?" : "Already have an account?"}
          <button
            onClick={() => setIsLogin(!isLogin)}
            className="ml-1 text-blue-600 hover:text-blue-800"
          >
            {isLogin ? 'Register' : 'Login'}
          </button>
        </p>
      </div>
    </div>
  );
};

const CartDropdown = ({ onClose }) => {
  const { cart, removeFromCart } = useAppContext();

  const checkout = async () => {
    if (cart.items.length === 0) {
      alert('Your cart is empty');
      return;
    }

    const email = prompt('Please enter your email for checkout:');
    if (!email) return;

    try {
      const response = await axios.post(`${API}/orders/create?session_id=${localStorage.getItem('sessionId')}`, {
        user_email: email,
        payment_method: 'CREDIT_CARD'
      });

      window.open(response.data.payment_url, '_blank');
      onClose();
    } catch (error) {
      alert('Checkout failed: ' + (error.response?.data?.detail || error.message));
    }
  };

  return (
    <div className="absolute right-0 top-full mt-2 w-96 bg-white rounded-lg shadow-xl border z-50 mr-4">
      <div className="p-4">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Shopping Cart</h3>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
        </div>
        
        {cart.items.length === 0 ? (
          <p className="text-gray-500 text-center py-4">Your cart is empty</p>
        ) : (
          <>
            <div className="space-y-3 max-h-64 overflow-y-auto">
              {cart.items.map((item) => (
                <div key={item.id} className="flex justify-between items-center p-2 border-b">
                  <div className="flex-1">
                    <h4 className="font-medium text-sm">{item.product.name}</h4>
                    <p className="text-xs text-gray-500">
                      Qty: {item.quantity} × IDR {item.price.toLocaleString('id-ID')}
                    </p>
                  </div>
                  <div className="flex items-center space-x-2">
                    <span className="font-medium text-sm">
                      IDR {item.total.toLocaleString('id-ID')}
                    </span>
                    <button
                      onClick={() => removeFromCart(item.id)}
                      className="text-red-500 hover:text-red-700 text-xs"
                    >
                      Remove
                    </button>
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-4 pt-4 border-t">
              <div className="flex justify-between items-center mb-4">
                <span className="font-semibold">Total: IDR {cart.total.toLocaleString('id-ID')}</span>
              </div>
              <button
                onClick={checkout}
                className="w-full bg-green-600 text-white py-2 rounded-lg hover:bg-green-700 transition-colors"
              >
                Checkout with Xendit
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

const HeroSection = () => {
  return (
    <section id="home" className="bg-gradient-to-br from-blue-600 to-blue-800 text-white py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <h1 className="text-4xl md:text-6xl font-bold mb-6">
              Shop Smart, Pay Easy with Xendit
            </h1>
            <p className="text-xl mb-8 text-blue-100">
              Discover amazing products and services with secure Indonesian payment methods. 
              QRIS, Bank Transfer, E-Wallets, and more!
            </p>
            <div className="flex flex-wrap gap-4">
              <a href="#products" className="bg-white text-blue-600 px-8 py-3 rounded-lg font-semibold hover:bg-blue-50 transition-colors">
                Shop Now
              </a>
              <a href="#subscriptions" className="border-2 border-white text-white px-8 py-3 rounded-lg font-semibold hover:bg-white hover:text-blue-600 transition-colors">
                View Subscriptions
              </a>
            </div>
          </div>
          <div className="flex justify-center">
            <img 
              src="https://images.pexels.com/photos/7563569/pexels-photo-7563569.jpeg" 
              alt="E-commerce Hero" 
              className="rounded-lg shadow-2xl max-w-md w-full"
            />
          </div>
        </div>
      </div>
    </section>
  );
};

const ProductsSection = () => {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const { addToCart } = useAppContext();

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await axios.get(`${API}/products`);
      setProducts(response.data);
    } catch (error) {
      console.error('Error fetching products:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <section className="py-20 bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading products...</p>
        </div>
      </section>
    );
  }

  return (
    <section id="products" className="py-20 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Featured Products & Packages
          </h2>
          <p className="text-xl text-gray-600">
            Choose from our carefully selected products and service packages
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {products.map((product) => (
            <div key={product.id} className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition-shadow">
              <div className="aspect-w-16 aspect-h-9">
                <img 
                  src={product.images[0] || 'https://images.pexels.com/photos/6995253/pexels-photo-6995253.jpeg'} 
                  alt={product.name}
                  className="w-full h-48 object-cover"
                />
              </div>
              <div className="p-6">
                <span className="inline-block bg-blue-100 text-blue-800 text-xs px-2 py-1 rounded-full uppercase tracking-wider font-semibold mb-2">
                  {product.category}
                </span>
                <h3 className="text-xl font-bold text-gray-900 mb-2">{product.name}</h3>
                <p className="text-gray-600 mb-4">{product.description}</p>
                <div className="flex justify-between items-center">
                  <span className="text-2xl font-bold text-blue-600">
                    IDR {product.price.toLocaleString('id-ID')}
                  </span>
                  <button
                    onClick={() => addToCart(product.id)}
                    className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Add to Cart
                  </button>
                </div>
                <p className="text-sm text-gray-500 mt-2">Stock: {product.stock} available</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

const SubscriptionsSection = () => {
  const [plans, setPlans] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPlans();
  }, []);

  const fetchPlans = async () => {
    try {
      const response = await axios.get(`${API}/subscription-plans`);
      setPlans(response.data);
    } catch (error) {
      console.error('Error fetching subscription plans:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <section className="py-20">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading subscription plans...</p>
        </div>
      </section>
    );
  }

  return (
    <section id="subscriptions" className="py-20">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Subscription Plans
          </h2>
          <p className="text-xl text-gray-600">
            Choose a plan that fits your needs with flexible billing
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
          {plans.map((plan, index) => (
            <div key={plan.id} className={`bg-white rounded-lg shadow-lg p-8 ${index === 1 ? 'ring-2 ring-blue-500 relative' : ''}`}>
              {index === 1 && (
                <div className="absolute -top-4 left-1/2 transform -translate-x-1/2">
                  <span className="bg-blue-500 text-white px-4 py-1 rounded-full text-sm font-semibold">
                    Most Popular
                  </span>
                </div>
              )}
              
              <div className="text-center">
                <h3 className="text-2xl font-bold text-gray-900 mb-4">{plan.name}</h3>
                <p className="text-gray-600 mb-6">{plan.description}</p>
                <div className="mb-6">
                  <span className="text-4xl font-bold text-blue-600">
                    IDR {plan.price.toLocaleString('id-ID')}
                  </span>
                  <span className="text-gray-500">/{plan.billing_cycle}</span>
                </div>
                
                <ul className="space-y-3 mb-8">
                  {plan.features.map((feature, featureIndex) => (
                    <li key={featureIndex} className="flex items-center">
                      <svg className="w-5 h-5 text-green-500 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
                      </svg>
                      {feature}
                    </li>
                  ))}
                </ul>
                
                <button className={`w-full py-3 px-6 rounded-lg font-semibold transition-colors ${
                  index === 1 
                    ? 'bg-blue-600 text-white hover:bg-blue-700' 
                    : 'bg-gray-100 text-gray-900 hover:bg-gray-200'
                }`}>
                  Choose {plan.name}
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

const PaymentMethodsSection = () => {
  return (
    <section className="py-20 bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
            Secure Payment Methods
          </h2>
          <p className="text-xl text-gray-600">
            Pay securely with your preferred Indonesian payment method
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
          <div className="text-center">
            <div className="bg-white rounded-lg p-6 shadow-lg">
              <img 
                src="https://images.pexels.com/photos/9169180/pexels-photo-9169180.jpeg" 
                alt="QRIS Payment" 
                className="w-16 h-16 mx-auto mb-4 rounded-lg"
              />
              <h3 className="font-semibold text-gray-900">QRIS</h3>
              <p className="text-sm text-gray-600">Quick Response Indonesian Standard</p>
            </div>
          </div>
          
          <div className="text-center">
            <div className="bg-white rounded-lg p-6 shadow-lg">
              <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-lg flex items-center justify-center">
                <span className="text-green-600 font-bold text-xs">BANK</span>
              </div>
              <h3 className="font-semibold text-gray-900">Bank Transfer</h3>
              <p className="text-sm text-gray-600">All major Indonesian banks</p>
            </div>
          </div>
          
          <div className="text-center">
            <div className="bg-white rounded-lg p-6 shadow-lg">
              <div className="w-16 h-16 mx-auto mb-4 bg-blue-100 rounded-lg flex items-center justify-center">
                <span className="text-blue-600 font-bold text-xs">CARD</span>
              </div>
              <h3 className="font-semibold text-gray-900">Credit Card</h3>
              <p className="text-sm text-gray-600">Visa, Mastercard</p>
            </div>
          </div>
          
          <div className="text-center">
            <div className="bg-white rounded-lg p-6 shadow-lg">
              <div className="w-16 h-16 mx-auto mb-4 bg-purple-100 rounded-lg flex items-center justify-center">
                <span className="text-purple-600 font-bold text-xs">WALLET</span>
              </div>
              <h3 className="font-semibold text-gray-900">E-Wallets</h3>
              <p className="text-sm text-gray-600">DANA, OVO, LinkAja</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

const Footer = () => {
  return (
    <footer className="bg-gray-900 text-white py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-lg font-bold mb-4">ShopINA</h3>
            <p className="text-gray-400">
              Your trusted Indonesian e-commerce platform with secure Xendit payment integration.
            </p>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Quick Links</h4>
            <ul className="space-y-2 text-gray-400">
              <li><a href="#home" className="hover:text-white">Home</a></li>
              <li><a href="#products" className="hover:text-white">Products</a></li>
              <li><a href="#subscriptions" className="hover:text-white">Subscriptions</a></li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Payment</h4>
            <ul className="space-y-2 text-gray-400">
              <li>QRIS</li>
              <li>Bank Transfer</li>
              <li>Credit Card</li>
              <li>E-Wallets</li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Contact</h4>
            <ul className="space-y-2 text-gray-400">
              <li>Email: support@shopina.com</li>
              <li>Phone: +62 21 1234 5678</li>
              <li>Jakarta, Indonesia</li>
            </ul>
          </div>
        </div>
        
        <div className="border-t border-gray-800 mt-8 pt-8 text-center text-gray-400">
          <p>&copy; 2025 ShopINA. All rights reserved. Powered by Xendit.</p>
        </div>
      </div>
    </footer>
  );
};

// Initialize sample data
const initializeSampleData = async () => {
  try {
    await axios.post(`${API}/admin/init-data`);
  } catch (error) {
    console.error('Error initializing sample data:', error);
  }
};

// Main App Component
function App() {
  useEffect(() => {
    initializeSampleData();
  }, []);

  return (
    <AppProvider>
      <div className="App">
        <Header />
        <HeroSection />
        <ProductsSection />
        <SubscriptionsSection />
        <PaymentMethodsSection />
        <Footer />
      </div>
    </AppProvider>
  );
}

export default App;