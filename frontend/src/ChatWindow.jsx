import React, { useState, useRef, useEffect } from 'react';
import {
  Send, Upload, FileText, Trash2, Settings, Download, User, Bot, Sparkles,
  Brain, Zap, MessageCircle, Plus, X, Loader, CheckCircle, AlertCircle,
  LogOut, Menu, Home, BarChart3
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const ChatWindow = () => {
  // ─── read logged-in user ───────────────────────────────────────────────────
  const [user, setUser] = useState({ username: 'demo_user' }); // Mock user for demo

    useEffect(() => {
      const raw = localStorage.getItem('user');
      if (!raw) return window.location.href = '/';
      try {
        setUser(JSON.parse(raw));
      } catch {
        window.location.href = '/';
      }
    }, []);
  
  
  // ─── UI state ───────────────────────────────────────────────────────────────
  const [messages, setMessages] = useState([{
    id: 1,
    type: 'bot',
    content: `Hello! I'm your AI assistant. Upload documents to train me on your specific content, and I'll help answer questions based on that knowledge.`,
    timestamp: new Date(),
    animated: false
  }]);
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [trainingStatus, setTrainingStatus] = useState('idle');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState({});
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };
  useEffect(scrollToBottom, [messages]);

  // ─── helpers ────────────────────────────────────────────────────────────────
  const formatFileSize = bytes => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes','KB','MB','GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
  };

  // ─── 1) send chat message ───────────────────────────────────────────────────
const handleSendMessage = async () => {
  if (!inputMessage.trim()) return;

  const userMsg = {
    id: Date.now(),
    type: 'user',
    content: inputMessage,
    timestamp: new Date(),
    animated: true
  };
  setMessages(m => [...m, userMsg]);
  setInputMessage('');
  setIsTyping(true);
  
  console.log(user.username)
  console.log(inputMessage)
  
  try {
    const res = await fetch("http://localhost:8000/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user: user.username, 
        question: inputMessage  // ← Changed from "inputMessage" to "question"
      })
    });
    
    const { answer } = await res.json();
    setMessages(m => [
      ...m,
      { id: Date.now()+1, type: 'bot', content: answer, timestamp: new Date(), animated: true }
    ]);
  } catch {
    setMessages(m => [
      ...m,
      { id: Date.now()+1, type: 'bot', content: "⚠️ Server error", timestamp: new Date(), animated: true }
    ]);
  } finally {
    setIsTyping(false);
  }
};

  // ─── 2) upload files with improved UX ─────────────────────────────────────────
const handleFileUpload = async (files) => {
  if (!files?.length) return;

  setIsUploading(true);

  // 1️⃣ Initialize file items in state
  const fileItems = Array.from(files).map((file) => ({
    id: Date.now() + Math.random(),
    name: file.name,
    size: file.size,
    status: 'pending',
    file,
  }));
  setUploadedFiles((prev) => [...prev, ...fileItems]);

  // 2️⃣ Process each file one by one
  for (const item of fileItems) {
    // mark as “uploading”
    setUploadedFiles((prev) =>
      prev.map((f) =>
        f.id === item.id
          ? { ...f, status: 'uploading' }
          : f
      )
    );

    // perform the upload
    const formData = new FormData();
    formData.append('user', user.username);
    formData.append('files', item.file);

    let uploadRes;
    try {
      uploadRes = await fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
      });
    } catch (err) {
      uploadRes = { ok: false, statusText: err.message };
    }

    if (!uploadRes.ok) {
      // mark as failed
      setUploadedFiles((prev) =>
        prev.map((f) =>
          f.id === item.id
            ? { ...f, status: 'failed' }
            : f
        )
      );
      continue; // go to next file
    }

    // simulate server-side processing time
    setUploadedFiles((prev) =>
      prev.map((f) =>
        f.id === item.id
          ? { ...f, status: 'processing' }
          : f
      )
    );
    await new Promise((r) => setTimeout(r, 1500));

    // finally mark completed
    setUploadedFiles((prev) =>
      prev.map((f) =>
        f.id === item.id
          ? { ...f, status: 'completed' }
          : f
      )
    );
  }

  setIsUploading(false);

  // 3️⃣ All done: close modal & send bot message
  setShowUploadModal(false);
  setMessages((prev) => [
    ...prev,
    {
      id: Date.now() + Math.random(),
      type: 'bot',
      content: `🎉 Successfully processed ${fileItems.length} document${fileItems.length > 1 ? 's' : ''}! I’m now ready to answer questions based on your uploaded content.`,
      timestamp: new Date(),
      animated: true,
    },
  ]);
};

  const handleDrop = e => { 
    e.preventDefault(); 
    setDragOver(false); 
    handleFileUpload(e.dataTransfer.files); 
  };
  
  const handleDragOver = e => { 
    e.preventDefault(); 
    setDragOver(true); 
  };
  
  const handleDragLeave = e => { 
    e.preventDefault(); 
    setDragOver(false); 
  };

  const removeFile = fileId => {
    setUploadedFiles(f => f.filter(x => x.id !== fileId));
  };

  // ─── 4) export chat ──────────────────────────────────────────────────────────
  const exportChat = () => {
    const chatData = messages.map(m => ({
      type: m.type,
      content: m.content,
      timestamp: m.timestamp.toISOString()
    }));
    const blob = new Blob([JSON.stringify(chatData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'chat-export.json'; a.click();
    URL.revokeObjectURL(url);
  };

  // ─── 5) sign out ─────────────────────────────────────────────────────────────
  const handleSignOut = async () => {
      try {
    const res = await fetch("http://localhost:8000/logout", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ user: user.username })
    });

    if (!res.ok) {
      console.error("Logout failed:",await res.text());
      return;
    }

    // Clear everything that might indicate “logged in”
    localStorage.removeItem("user");
    // (if you use any other storage)
    // sessionStorage.clear();
    // cookies via your auth lib…

    // Then force the navigation
    window.location.href = "/";
  } catch (err) {
    console.error("Logout error:", err);
  }

    console.log('Signing out...');
  };

  const getFileStatusIcon = (status) => {
    switch (status) {
      case 'uploading':
        return <Loader className="w-4 h-4 text-blue-400 animate-spin" />;
      case 'processing':
        return <Loader className="w-4 h-4 text-yellow-400 animate-spin" />;
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      default:
        return null;
    }
  };

  const getFileStatusText = (status) => {
    switch (status) {
      case 'uploading':
        return 'Uploading...';
      case 'processing':
        return 'Processing...';
      case 'completed':
        return 'Ready';
      case 'error':
        return 'Failed';
      default:
        return 'Pending';
    }
  };

  // ─── render ─────────────────────────────────────────────────────────────────
  return (
    <div className="h-screen bg-gradient-to-br from-gray-900 via-purple-900 to-violet-900 relative overflow-hidden flex flex-col">
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -inset-10 opacity-20">
          <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-purple-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse"></div>
          <div className="absolute top-3/4 right-1/4 w-96 h-96 bg-violet-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse animation-delay-2000"></div>
          <div className="absolute bottom-1/4 left-1/3 w-96 h-96 bg-indigo-500 rounded-full mix-blend-multiply filter blur-xl animate-pulse animation-delay-4000"></div>
        </div>
      </div>

      {/* Header */}
      <div className="relative z-10 bg-black/20 backdrop-blur-xl border-b border-white/10 flex-shrink-0">
        <div className="max-w-full mx-auto px-4 sm:px-6 py-4">
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div className="flex items-center space-x-3 min-w-0">
              <div className="w-10 h-10 bg-gradient-to-r from-purple-600 to-violet-600 rounded-xl flex items-center justify-center flex-shrink-0">
                <Sparkles className="w-6 h-6 text-white" />
              </div>
              <div className="min-w-0">
                <h1 className="text-white text-lg sm:text-xl font-bold truncate">AI Assistant Dashboard</h1>
                <p className="text-gray-400 text-xs sm:text-sm truncate">Intelligent document-based conversations</p>
              </div>
            </div>
            
            <div className="flex items-center space-x-2 sm:space-x-4 flex-shrink-0">
              <button 
                onClick={() => setShowUploadModal(true)} 
                className="flex items-center px-3 sm:px-4 py-2 bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700 rounded-lg text-white font-medium transition-all duration-300 transform hover:scale-105 text-sm"
              >
                <Upload className="w-4 h-4 mr-1 sm:mr-2" /> 
                <span className="hidden sm:inline">Upload Documents</span>
                <span className="sm:hidden">Upload</span>
              </button>
              
              <button 
                onClick={exportChat} 
                className="flex items-center px-3 sm:px-4 py-2 bg-gradient-to-r from-blue-600 to-cyan-600 hover:from-blue-700 hover:to-cyan-700 rounded-lg text-white font-medium transition-all duration-300 transform hover:scale-105 text-sm"
              >
                <Download className="w-4 h-4 mr-1 sm:mr-2" /> 
                <span className="hidden sm:inline">Export</span>
              </button>
              
              <div className="hidden sm:block h-6 w-px bg-white/20"></div>
              
              <div className="flex items-center space-x-2 sm:space-x-3">
                <div className="w-8 h-8 bg-gradient-to-r from-purple-600 to-violet-600 rounded-full flex items-center justify-center">
                  <User className="w-4 h-4 text-white" />
                </div>
                <span className="text-white font-medium text-sm hidden sm:inline">{user.username}</span>
              </div>
              
              <button 
                type="button" 
                onClick={handleSignOut} 
                className="flex items-center px-3 sm:px-4 py-2 bg-gradient-to-r from-red-600 to-pink-600 hover:from-red-700 hover:to-pink-700 rounded-lg text-white font-medium transition-all duration-300 transform hover:scale-105 text-sm"
              >
                <LogOut className="w-4 h-4 mr-1 sm:mr-2" /> 
                <span className="hidden sm:inline">Sign Out</span>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="relative z-10 flex-1 overflow-hidden">
        <div className="h-full max-w-full mx-auto p-4 sm:p-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 sm:gap-6 h-full">
            
            {/* Stats Panel - Hidden on mobile, shown on large screens */}
            <div className="hidden lg:block lg:col-span-3 space-y-6 overflow-y-auto">
              <div className="bg-black/20 backdrop-blur-xl border border-white/10 rounded-xl p-6">
                <h3 className="text-white font-semibold mb-4 flex items-center">
                  <BarChart3 className="w-5 h-5 mr-2" /> Chat Statistics
                </h3>
                <div className="space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Total Messages</span>
                    <span className="text-purple-400 font-semibold">{messages.length}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">Documents</span>
                    <span className="text-purple-400 font-semibold">{uploadedFiles.length}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300">AI Status</span>
                    <span className={`font-semibold ${
                      uploadedFiles.some(f => f.status === 'completed') ? 'text-green-400' :
                      uploadedFiles.some(f => f.status === 'processing' || f.status === 'uploading') ? 'text-yellow-400' : 'text-gray-400'
                    }`}>
                      {uploadedFiles.some(f => f.status === 'completed') ? 'Trained' :
                       uploadedFiles.some(f => f.status === 'processing' || f.status === 'uploading') ? 'Processing...' : 'Ready'}
                    </span>
                  </div>
                </div>
              </div>

              {/* Document List */}
              <div className="bg-black/20 backdrop-blur-xl border border-white/10 rounded-xl p-6 flex-1 min-h-0">
                <h3 className="text-white font-semibold mb-4 flex items-center">
                  <FileText className="w-5 h-5 mr-2" /> Documents ({uploadedFiles.length})
                </h3>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {uploadedFiles.length === 0 ? (
                    <div className="text-center py-8 text-gray-400">
                      <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                      <p className="text-sm">No documents uploaded yet</p>
                      <button 
                        onClick={() => setShowUploadModal(true)} 
                        className="mt-2 text-purple-400 hover:text-purple-300 text-sm font-medium"
                      >
                        Upload your first document
                      </button>
                    </div>
                  ) : uploadedFiles.map(f => (
                    <div key={f.id} className="flex items-center p-3 bg-black/30 rounded-lg border border-white/5">
                      <FileText className="w-4 h-4 text-gray-400 mr-3 flex-shrink-0" />
                      <div className="flex-1 min-w-0">
                        <p className="text-white text-sm truncate">{f.name}</p>
                        <div className="flex items-center justify-between">
                          <p className="text-gray-400 text-xs">{formatFileSize(f.size)}</p>
                          <p className="text-xs text-gray-400">{getFileStatusText(f.status)}</p>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2 ml-2 flex-shrink-0">
                        {getFileStatusIcon(f.status)}
                        {f.status === 'completed' && (
                          <button 
                            onClick={() => removeFile(f.id)} 
                            className="text-red-400 hover:text-red-300"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Chat Window */}
            <div className="col-span-1 lg:col-span-9 bg-black/20 backdrop-blur-xl border border-white/10 rounded-xl flex flex-col min-h-0">
              {/* Chat Header */}
              <div className="border-b border-white/10 p-4 flex-shrink-0">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-gradient-to-r from-purple-600 to-violet-600 rounded-full flex items-center justify-center">
                      <Bot className="w-5 h-5 text-white" />
                    </div>
                    <div>
                      <h2 className="text-white font-semibold">AI Assistant</h2>
                      <p className="text-gray-400 text-xs sm:text-sm">
                        {uploadedFiles.some(f => f.status === 'completed')
                          ? `Trained on ${uploadedFiles.filter(f => f.status === 'completed').length} documents`
                          : 'Ready to help you'}
                      </p>
                    </div>
                  </div>
                  {uploadedFiles.some(f => f.status === 'completed') && (
                    <div className="px-3 py-1 bg-green-600/20 border border-green-500/30 rounded-full text-green-400 text-xs font-medium">
                      <Zap className="w-3 h-3 inline mr-1" /> AI Trained
                    </div>
                  )}
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 min-h-0">
                {messages.map(msg => (
                  <div key={msg.id} className={`flex ${msg.type==='user'?'justify-end':'justify-start'} ${msg.animated?'animate-slideUp':''}`}>
                    <div className={`flex items-start space-x-3 max-w-2xl ${msg.type==='user'?'flex-row-reverse space-x-reverse':''}`}>
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                        msg.type==='user'
                          ? 'bg-gradient-to-r from-blue-600 to-cyan-600'
                          : 'bg-gradient-to-r from-purple-600 to-violet-600'
                      }`}>
                        {msg.type==='user'
                          ? <User className="w-4 h-4 text-white" />
                          : <Bot className="w-4 h-4 text-white" />}
                      </div>
                      <div className={`px-4 py-3 rounded-2xl ${
                        msg.type==='user'
                          ? 'bg-gradient-to-r from-blue-600 to-cyan-600 text-white'
                          : 'bg-black/30 backdrop-blur-sm text-gray-100 border border-white/10'
                      }`}>
                        <p className="text-sm leading-relaxed">{msg.content}</p>
                        <p className={`text-xs mt-2 ${msg.type==='user'?'text-blue-100':'text-gray-400'}`}>
                          {msg.timestamp.toLocaleTimeString()}
                        </p>
                      </div>
                    </div>
                  </div>
                ))}
                {isTyping && (
                  <div className="flex justify-start animate-slideUp">
                    <div className="flex items-start space-x-3 max-w-2xl">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-r from-purple-600 to-violet-600 flex items-center justify-center">
                        <Bot className="w-4 h-4 text-white" />
                      </div>
                      <div className="px-4 py-3 rounded-2xl bg-black/30 backdrop-blur-sm border border-white/10">
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"></div>
                          <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce animation-delay-200"></div>
                          <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce animation-delay-400"></div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              {/* Input */}
              <div className="border-t border-white/10 p-4 flex-shrink-0">
                <div className="flex items-center space-x-3">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={e => setInputMessage(e.target.value)}
                    onKeyPress={e => e.key==='Enter' && handleSendMessage()}
                    placeholder="Type your message..."
                    className="w-full px-4 py-3 bg-black/30 backdrop-blur-sm border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:border-purple-500 focus:ring-2 focus:ring-purple-500/20 transition-all duration-300"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!inputMessage.trim()||isTyping}
                    className="p-3 bg-gradient-to-r from-purple-600 to-violet-600 hover:from-purple-700 hover:to-violet-700 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed rounded-xl text-white transition-all duration-300 transform hover:scale-105 disabled:hover:scale-100 flex-shrink-0"
                  >
                    <Send className="w-5 h-5" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-black/80 backdrop-blur-xl border border-white/20 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-white text-xl font-semibold flex items-center">
                  <Upload className="w-6 h-6 mr-2" /> Upload Documents
                </h2>
                <button 
                  onClick={() => setShowUploadModal(false)} 
                  className="text-gray-400 hover:text-white transition-colors"
                  disabled={isUploading}
                >
                  <X className="w-6 h-6" />
                </button>
              </div>
              
              <div
                className={`border-2 border-dashed rounded-xl p-8 text-center mb-6 transition-all duration-300 ${
                  dragOver ? 'border-purple-400 bg-purple-500/20' : 'border-gray-600 hover:border-purple-500 hover:bg-purple-500/10'
                }`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
              >
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <p className="text-gray-300 text-lg mb-2">Drop files here or</p>
                <button
                  onClick={() => fileInputRef.current.click()}
                  disabled={isUploading}
                  className="px-6 py-3 bg-gradient-to-r from-purple-600 to-violet-600 rounded-lg text-white font-medium hover:from-purple-700 hover:to-violet-700 transition-all duration-300 transform hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                  {isUploading ? 'Uploading...' : 'Browse Files'}
                </button>
                <p className="text-gray-400 text-sm mt-3">Supports PDF, DOC, DOCX, TXT, MD files</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  accept=".pdf,.doc,.docx,.txt,.md"
                  onChange={e => handleFileUpload(e.target.files)}
                  className="hidden"
                  disabled={isUploading}
                />
              </div>
              
              {uploadedFiles.length > 0 && (
                <div className="mb-6">
                  <h3 className="text-white font-medium mb-4">Files ({uploadedFiles.length})</h3>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {uploadedFiles.map(f => (
                      <div key={f.id} className="flex items-center p-3 bg-black/30 rounded-lg">
                        <FileText className="w-5 h-5 text-gray-400 mr-3 flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-white text-sm truncate">{f.name}</p>
                          <div className="flex items-center justify-between">
                            <p className="text-gray-400 text-xs">{formatFileSize(f.size)}</p>
                            <p className={`text-xs font-medium ${
                              f.status === 'uploading' ? 'text-blue-400' :
                              f.status === 'processing' ? 'text-yellow-400' :
                              f.status === 'completed' ? 'text-green-400' :
                              f.status === 'error' ? 'text-red-400' : 'text-gray-400'
                            }`}>
                              {getFileStatusText(f.status)}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-2 ml-2 flex-shrink-0">
                          {getFileStatusIcon(f.status)}
                          {f.status === 'completed' && (
                            <button 
                              onClick={() => removeFile(f.id)} 
                              className="text-red-400 hover:text-red-300"
                            >
                              <X className="w-4 h-4" />
                            </button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {isUploading && (
                <div className="text-center py-4">
                  <div className="inline-flex items-center px-6 py-3 bg-purple-600/20 border border-purple-500/30 rounded-lg text-purple-400">
                    <Loader className="w-5 h-5 mr-3 animate-spin" />
                    Processing documents...
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};
  export default ChatWindow;
  
