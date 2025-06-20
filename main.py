import os
import requests
import json
import hashlib
import pickle
from typing import List, Dict, Any
from dotenv import load_dotenv

# Lightweight text processing
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Simple document loaders
import PyPDF2
from docx import Document as DocxDocument

class APIBasedChatBot:
    def __init__(self, file_paths: List[str] = None):
        load_dotenv()
        
        # API configurations - use lightweight API services
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.groq_api_key = os.getenv("GROQ_API_KEY")  # Free tier available
        self.together_api_key = os.getenv("TOGETHER_API_KEY")  # Free tier available
        
        # Initialize document store
        self.documents = []
        self.vectorizer = None
        self.tfidf_matrix = None
        
        if file_paths:
            self._load_and_process_documents(file_paths)
    
    def _load_and_process_documents(self, file_paths: List[str]):
        """Load documents with memory-efficient processing"""
        all_chunks = []
        
        for path in file_paths:
            try:
                # Size check
                if os.path.getsize(path) > 5 * 1024 * 1024:  # 5MB max
                    continue
                
                text = self._extract_text(path)
                if text:
                    chunks = self._chunk_text(text, chunk_size=400)
                    for i, chunk in enumerate(chunks):
                        all_chunks.append({
                            'content': chunk,
                            'source': os.path.basename(path),
                            'chunk_id': i
                        })
                
                # Limit total chunks to save memory
                if len(all_chunks) > 150:
                    break
                    
            except Exception as e:
                print(f"Error processing {path}: {e}")
                continue
        
        self.documents = all_chunks
        self._create_vector_index()
    
    def _extract_text(self, file_path: str) -> str:
        """Extract text from various file formats"""
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.txt':
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
            
            elif ext == '.pdf':
                text = ""
                with open(file_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    # Limit to first 20 pages to save memory
                    for page_num, page in enumerate(reader.pages[:20]):
                        text += page.extract_text()
                return text
            
            elif ext in ['.docx', '.doc']:
                doc = DocxDocument(file_path)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            
            else:
                # Try reading as text
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    return f.read()
                    
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def _chunk_text(self, text: str, chunk_size: int = 400) -> List[str]:
        """Simple text chunking"""
        import re
        
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Split into sentences
        sentences = re.split(r'[.!?]+', text)
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            if len(current_chunk) + len(sentence) < chunk_size:
                current_chunk += sentence + ". "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return [chunk for chunk in chunks if len(chunk) > 20]
    
    def _create_vector_index(self):
        """Create lightweight vector index using TF-IDF"""
        if not self.documents:
            return
        
        texts = [doc['content'] for doc in self.documents]
        
        # Use TF-IDF for similarity search (much lighter than embeddings)
        self.vectorizer = TfidfVectorizer(
            max_features=2000,
            stop_words='english',
            lowercase=True,
            ngram_range=(1, 2),
            min_df=1,
            max_df=0.95
        )
        
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
    
    def _get_relevant_context(self, question: str, top_k: int = 3) -> str:
        """Retrieve relevant context using TF-IDF similarity"""
        if not self.documents or self.tfidf_matrix is None:
            return ""
        
        # Vectorize question
        question_vector = self.vectorizer.transform([question])
        
        # Calculate similarities
        similarities = cosine_similarity(question_vector, self.tfidf_matrix)[0]
        
        # Get top k most similar chunks
        top_indices = np.argsort(similarities)[-top_k:][::-1]
        
        relevant_chunks = []
        for idx in top_indices:
            if similarities[idx] > 0.1:  # Minimum similarity threshold
                relevant_chunks.append(self.documents[idx]['content'])
        
        return "\n\n".join(relevant_chunks)
    
    def _call_groq_api(self, prompt: str) -> str:
        """Call Groq API (free tier available, very fast)"""
        if not self.groq_api_key:
            return "Groq API key not configured"
        
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama3-8b-8192",  # Fast and free
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 200,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except Exception as e:
            return f"Error calling Groq API: {str(e)}"
    
    def _call_together_api(self, prompt: str) -> str:
        """Call Together AI API (free tier available)"""
        if not self.together_api_key:
            return "Together API key not configured"
        
        url = "https://api.together.xyz/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.together_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 200,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except Exception as e:
            return f"Error calling Together API: {str(e)}"
    
    def _call_openai_api(self, prompt: str) -> str:
        """Call OpenAI API (paid but reliable)"""
        if not self.openai_api_key:
            return "OpenAI API key not configured"
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "gpt-3.5-turbo",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 200,
            "temperature": 0.7
        }
        
        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except Exception as e:
            return f"Error calling OpenAI API: {str(e)}"
    
    def ask(self, question: str) -> str:
        """Answer question using RAG with API-based LLM"""
        if not self.documents:
            return "No documents loaded. Please upload documents first."
        
        # Step 1: Retrieve relevant context
        context = self._get_relevant_context(question, top_k=3)
        
        if not context:
            return "I couldn't find relevant information in the uploaded documents."
        
        # Step 2: Create prompt for LLM
        prompt = f"""Based on the following context from uploaded documents, answer the question concisely.

Context:
{context}

Question: {question}

Instructions:
- Answer based only on the provided context
- If the context doesn't contain the answer, say "I don't have enough information to answer this question"
- Keep the answer concise (1-3 sentences)
- Don't make up information not in the context

Answer:"""
        
        # Step 3: Try different APIs in order of preference
        # 1. Try Groq first (fastest and free)
        if self.groq_api_key:
            response = self._call_groq_api(prompt)
            if not response.startswith("Error") and not response.startswith("Groq API key"):
                return response
        
        # 2. Try Together AI (free tier)
        if self.together_api_key:
            response = self._call_together_api(prompt)
            if not response.startswith("Error") and not response.startswith("Together API key"):
                return response
        
        # 3. Try OpenAI (paid but reliable)
        if self.openai_api_key:
            response = self._call_openai_api(prompt)
            if not response.startswith("Error") and not response.startswith("OpenAI API key"):
                return response
        
        # Fallback if no API is available
        return "No AI API configured. Please set up GROQ_API_KEY, TOGETHER_API_KEY, or OPENAI_API_KEY in your .env file."
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chatbot statistics"""
        return {
            "total_chunks": len(self.documents),
            "total_sources": len(set(doc['source'] for doc in self.documents)) if self.documents else 0,
            "apis_configured": {
                "groq": bool(self.groq_api_key),
                "together": bool(self.together_api_key),
                "openai": bool(self.openai_api_key)
            }
        }