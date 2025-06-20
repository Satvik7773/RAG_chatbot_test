import React, { useState, useEffect } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import ChatWindow from './ChatWindow.jsx';
const LoginApp = () => {
  const [isLogin, setIsLogin] = useState(true);
  const [isDarkMode, setIsDarkMode] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: ''
  });
  const [message, setMessage] = useState('');
  const [user, setUser] = useState(null);
  const [focusedField, setFocusedField] = useState('');
const API_BASE = import.meta.env.VITE_API_BASE;
  // Load theme preference on mount
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme');
    if (savedTheme === 'dark') {
      setIsDarkMode(true);
    }
      const savedUser = localStorage.getItem('user');
  if (savedUser) setUser(JSON.parse(savedUser));
  }, []);

  const toggleTheme = () => {
    setIsDarkMode(!isDarkMode);
    localStorage.setItem('theme', !isDarkMode ? 'dark' : 'light');
  };

  const handleChange = (e) => {
    setFormData({
      ...formData,
      [e.target.name]: e.target.value
    });
    // Clear message when user starts typing
    if (message) setMessage('');
  };

 const handleSubmit = async e => {
  e.preventDefault();
  setIsLoading(true);
    const emailPattern = /^\S+@\S+\.\S+$/;
  if (!emailPattern.test(formData.email)) {
    setMessage('Please enter a valid email address.');
    setIsLoading(false);
    return;
  }

  try {
    const endpoint = isLogin
      ? '/api/auth/login'
      : '/api/auth/register';

    const payload = isLogin
      ? { email: formData.email, password: formData.password }
      : formData;
   
    const res = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.message || 'Authentication failed');
    }

    const data = await res.json();
    setUser(data.user);
    setMessage(`Welcome ${isLogin ? 'back' : 'aboard'}! 🎉`);
      localStorage.setItem('user', JSON.stringify(data.user));

    setFormData({ username: '', email: '', password: '' });
  } catch (err) {
    setMessage(err.message);
  } finally {
    setIsLoading(false);
  }
};


  const handleLogout = () => {
    setUser(null);
    setMessage('See you later! 👋');
    localStorage.removeItem('user');
  };
   
 const handleGoogleSuccess = async (credentialResponse) => {
  setIsLoading(true);

  try {
    console.log('Posting to:', `api/auth/google`);
    console.log('ID Token:', credentialResponse.credential);


    const response = await fetch(`api/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ idToken: credentialResponse.credential }),
    });

    const text = await response.text();
    console.log('[Google /google] status:', response.status);
    console.log('[Google /google] body:', text);

    let parsed;
    try {
      parsed = JSON.parse(text);
    } catch (_err) {
      parsed = null;
    }

    if (!response.ok) {
      const errMsg = (parsed && parsed.message)
        ? parsed.message
        : `HTTP ${response.status}`;
      throw new Error(`Google login failed: ${errMsg}`);
    }

    const data = parsed; 
    setUser(data.user);
      localStorage.setItem('user', JSON.stringify(data.user));
    setMessage(`Welcome, ${data.user.username}! 🎉`);

  } catch (err) {
    console.error(err);
    setMessage(err.message);

  } finally {
    setIsLoading(false);
  }
};

const handleGoogleError = () => {
  setMessage('Google sign‑in was cancelled or failed');
};


  const switchMode = () => {
    setIsLogin(!isLogin);
    setMessage('');
    setFormData({ username: '', email: '', password: '' });
  };

  const themeClasses = isDarkMode 
    ? 'bg-gradient-to-br from-gray-900 via-purple-900 to-violet-900 text-white'
    : 'bg-gradient-to-br from-blue-50 via-indigo-100 to-purple-100 text-gray-800';

  const cardClasses = isDarkMode
    ? 'bg-gray-800 bg-opacity-80 backdrop-blur-lg border border-gray-700'
    : 'bg-white bg-opacity-80 backdrop-blur-lg border border-white';

  const inputClasses = isDarkMode
    ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400 focus:border-purple-500 focus:ring-purple-500'
    : 'bg-white border-gray-300 text-gray-800 placeholder-gray-500 focus:border-indigo-500 focus:ring-indigo-500';

  if (user) {
    return (
       <ChatWindow
        user={user}
        email={formData.email}
        isDarkMode={isDarkMode}
        toggleTheme={toggleTheme}
        handleLogout={handleLogout}
      />
    );
  }

  return (
    <div className={`min-h-screen ${themeClasses} flex items-center justify-center p-4 transition-all duration-500`}>
      <div className="max-w-7xl w-full grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        
        {/* Left Side - RAG Chatbot Info */}
        <div className="space-y-8 text-center lg:text-left order-2 lg:order-1">
          {/* Animated Background Elements */}
          <div className="absolute top-20 left-10 w-20 h-20 bg-purple-500 rounded-full opacity-10 animate-bounce"></div>
          <div className="absolute bottom-20 left-20 w-16 h-16 bg-pink-500 rounded-full opacity-10 animate-pulse"></div>
          
          <div className="space-y-6 relative z-10">
            <div className="inline-block">
              <div className="flex items-center space-x-3 mb-4">
                <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
                <span className={`text-sm font-semibold uppercase tracking-wider ${isDarkMode ? 'text-green-400' : 'text-green-600'}`}>
                  AI-Powered • Real-time • Smart
                </span>
              </div>
            </div>
            
            <h1 className="text-5xl lg:text-7xl font-black bg-gradient-to-r from-purple-400 via-pink-400 to-indigo-400 bg-clip-text text-transparent leading-tight">
              RAG-Based
              <br />
              <span className="text-4xl lg:text-6xl">Chatbot 🤖</span>
            </h1>
            
            <p className={`text-xl lg:text-2xl font-medium ${isDarkMode ? 'text-gray-300' : 'text-gray-600'} leading-relaxed max-w-2xl`}>
              Experience the future of AI conversations with our advanced <strong>Retrieval-Augmented Generation</strong> chatbot. 
              Get accurate, contextual responses powered by cutting-edge AI technology.
            </p>
            
            <div className="flex flex-wrap gap-3 justify-center lg:justify-start">
              <span className={`px-4 py-2 rounded-full text-sm font-semibold ${isDarkMode ? 'bg-purple-900 text-purple-300' : 'bg-purple-100 text-purple-700'}`}>
                📚 Document Search
              </span>
              <span className={`px-4 py-2 rounded-full text-sm font-semibold ${isDarkMode ? 'bg-pink-900 text-pink-300' : 'bg-pink-100 text-pink-700'}`}>
                🔍 Smart Retrieval
              </span>
              <span className={`px-4 py-2 rounded-full text-sm font-semibold ${isDarkMode ? 'bg-indigo-900 text-indigo-300' : 'bg-indigo-100 text-indigo-700'}`}>
                ⚡ Real-time AI
              </span>
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-12">
            <div className={`${cardClasses} p-6 rounded-2xl transform hover:scale-105 transition-all duration-300 hover:shadow-xl`}>
              <div className="text-4xl mb-4 animate-bounce">🧠</div>
              <h3 className="font-bold text-lg mb-3 bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
                Smart Retrieval
              </h3>

            </div>
            
            <div className={`${cardClasses} p-6 rounded-2xl transform hover:scale-105 transition-all duration-300 hover:shadow-xl`}>
              <div className="text-4xl mb-4 animate-pulse">⚡</div>
              <h3 className="font-bold text-lg mb-3 bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
                Lightning Fast
              </h3>
            </div>
            
            <div className={`${cardClasses} p-6 rounded-2xl transform hover:scale-105 transition-all duration-300 hover:shadow-xl`}>
              <div className="text-4xl mb-4 animate-spin" style={{animationDuration: '3s'}}>🎯</div>
              <h3 className="font-bold text-lg mb-3 bg-gradient-to-r from-purple-500 to-pink-500 bg-clip-text text-transparent">
                Contextual AI
              </h3>
            </div>
          </div>
        </div>

        {/* Right Side - Login/Signup Form */}
        <div className="order-1 lg:order-2 flex justify-center lg:justify-end">
          <div className={`${cardClasses} rounded-2xl shadow-2xl p-8 w-full max-w-md transform transition-all duration-500 hover:shadow-3xl relative overflow-hidden`}>
            
            {/* Animated Background Elements */}
            <div className="absolute -top-4 -right-4 w-24 h-24 bg-purple-500 rounded-full opacity-10 animate-bounce"></div>
            <div className="absolute -bottom-8 -left-8 w-32 h-32 bg-pink-500 rounded-full opacity-10 animate-pulse"></div>
            
            {/* Theme Toggle */}
            <button
              onClick={toggleTheme}
              className="absolute top-4 right-4 p-3 rounded-full bg-opacity-20 bg-gray-500 hover:bg-opacity-30 transition-all duration-200 text-2xl transform hover:scale-110"
            >
              {isDarkMode ? '☀️' : '🌙'}
            </button>

            <div className="text-center mb-8 relative z-10">
              <h2 className="text-4xl font-black mb-3 bg-gradient-to-r from-purple-600 via-pink-600 to-indigo-600 bg-clip-text text-transparent">
                {isLogin ? 'Welcome Back!' : 'Join the Future!'}
              </h2>
              <p className={`${isDarkMode ? 'text-gray-300' : 'text-gray-600'} font-medium text-lg`}>
                {isLogin ? 'Sign in to start chatting' : 'Create account to get started'}
              </p>
            </div>

            {message && (
              <div className={`p-4 rounded-xl mb-6 transform transition-all duration-300 ${
                message.includes('Welcome') || message.includes('aboard')
                  ? isDarkMode 
                    ? 'bg-green-900 border border-green-700 text-green-300'
                    : 'bg-green-50 border border-green-200 text-green-800'
                  : isDarkMode 
                    ? 'bg-red-900 border border-red-700 text-red-300'
                    : 'bg-red-50 border border-red-200 text-red-800'
              } animate-pulse`}>
                <div className="flex items-center">
                  <span className="mr-2 text-lg">
                    {message.includes('Welcome') || message.includes('aboard') ? '🎉' : '⚠️'}
                  </span>
                  {message}
                </div>
              </div>
            )}

            <div className="space-y-6 relative z-10">
              {!isLogin && (
                <div className="transform transition-all duration-300">
                  <label className={`block text-sm font-bold mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                    👤 Username
                  </label>
                  <input
                    type="text"
                    name="username"
                    value={formData.username}
                    onChange={handleChange}
                    onFocus={() => setFocusedField('username')}
                    onBlur={() => setFocusedField('')}
                    className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 transition-all duration-300 font-medium ${inputClasses} ${
                      focusedField === 'username' ? 'transform scale-105' : ''
                    }`}
                    placeholder="Choose a cool username"
                  />
                </div>
              )}

              <div className="transform transition-all duration-300">
                <label className={`block text-sm font-bold mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  📧 Email Address
                </label>
                <input
                  type="email"
                  name="email"
                  value={formData.email}
                  onChange={handleChange}
                  onFocus={() => setFocusedField('email')}
                  onBlur={() => setFocusedField('')}
                  className={`w-full px-4 py-3 border-2 rounded-xl focus:outline-none focus:ring-2 transition-all duration-300 font-medium ${inputClasses} ${
                    focusedField === 'email' ? 'transform scale-105' : ''
                  }`}
                  placeholder="your.email@example.com"
                />
              </div>

              <div className="transform transition-all duration-300">
                <label className={`block text-sm font-bold mb-2 ${isDarkMode ? 'text-gray-300' : 'text-gray-700'}`}>
                  🔒 Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    value={formData.password}
                    onChange={handleChange}
                    onFocus={() => setFocusedField('password')}
                    onBlur={() => setFocusedField('')}
                    className={`w-full px-4 py-3 pr-12 border-2 rounded-xl focus:outline-none focus:ring-2 transition-all duration-300 font-medium ${inputClasses} ${
                      focusedField === 'password' ? 'transform scale-105' : ''
                    }`}
                    placeholder="Enter secure password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-lg hover:scale-110 transition-transform duration-200"
                  >
                    {showPassword ? '🙈' : '👁️'}
                  </button>
                </div>
              </div>

              <button
                onClick={handleSubmit}
                disabled={isLoading}
                className={`w-full py-4 px-6 rounded-xl font-bold text-lg transition-all duration-300 transform hover:scale-105 shadow-lg ${
                  isLoading 
                    ? 'bg-gray-400 cursor-not-allowed'
                    : 'bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-white'
                }`}
              >
                {isLoading ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-white mr-2"></div>
                    Processing...
                  </div>
                ) : (
                  `${isLogin ? 'Sign In' : 'Create Account'} ${isLogin ? '🚀' : '✨'}`
                )}
              </button>
               
                 <div className="flex justify-center mt-4">
    <GoogleLogin
      onSuccess={handleGoogleSuccess}
      onError={handleGoogleError}
    />
  </div>


            </div>

            <div className="mt-8 text-center relative z-10">
              <p className={`${isDarkMode ? 'text-gray-400' : 'text-gray-600'} font-medium`}>
                {isLogin ? "New to our platform? " : "Already have an account? "}
                <button
                  onClick={switchMode}
                  className="text-purple-500 hover:text-purple-600 font-bold transition-colors duration-200 hover:underline"
                >
                  {isLogin ? 'Create Account' : 'Sign In'}
                </button>
              </p>
            </div>

            {/* Decorative Elements */}
            <div className="absolute top-1/2 left-0 w-1 h-16 bg-gradient-to-b from-purple-500 to-pink-500 rounded-r-full opacity-50"></div>
            <div className="absolute top-1/2 right-0 w-1 h-16 bg-gradient-to-b from-pink-500 to-purple-500 rounded-l-full opacity-50"></div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginApp;
