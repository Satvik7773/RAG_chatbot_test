import os
import hashlib
import pickle
from dotenv import load_dotenv
from typing import List, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

# LangChain loaders and utilities
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyPDFLoader   
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import HuggingFaceHub
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain.schema import Document

class OptimizedChatBot:
    # Class-level shared resources to avoid reloading
    _shared_embeddings: Optional[HuggingFaceEmbeddings] = None
    _shared_llm: Optional[HuggingFaceHub] = None
    _executor = ThreadPoolExecutor(max_workers=2)  # Limit concurrent operations
    
    def __init__(self, file_paths: List[str] = None, user_id: str = None):
        self.user_id = user_id or "default"
        
        # Initialize shared resources if not already done
        if not self._shared_embeddings or not self._shared_llm:
            self._init_shared_resources()
        
        # Process documents if provided
        if file_paths:
            self.docsearch = self._create_vectorstore(file_paths)
        else:
            self.docsearch = None
            
        self._setup_chain()
    
    @classmethod
    def _init_shared_resources(cls):
        """Initialize shared resources once across all instances"""
        load_dotenv()
        hf_key = os.getenv("HUGGINGFACE_API_KEY")
        if not hf_key:
            raise ValueError("Set HUGGINGFACE_API_KEY in .env")
        
        # Use smaller, faster embedding model
        if not cls._shared_embeddings:
            cls._shared_embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L12-v2",  # Smaller model
                model_kwargs={'device': 'cpu'},
                encode_kwargs={'normalize_embeddings': True, 'batch_size': 32}
            )
        
        # Use lighter LLM or switch to OpenAI-compatible API
        if not cls._shared_llm:
            cls._shared_llm = HuggingFaceHub(
                repo_id="microsoft/DialoGPT-medium",  # Lighter model
                model_kwargs={"temperature": 0.7, "max_length": 100},
                huggingfacehub_api_token=hf_key
            )
    
    def _create_vectorstore(self, file_paths: List[str]) -> FAISS:
        """Create vectorstore with caching and optimization"""
        
        # Create cache key based on file contents
        cache_key = self._get_cache_key(file_paths)
        cache_path = f"/tmp/vectorstore_{cache_key}.pkl"
        
        # Try to load from cache first
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'rb') as f:
                    return pickle.load(f)
            except:
                pass  # If cache fails, rebuild
        
        # Load and process documents
        docs = self._load_documents_optimized(file_paths)
        
        if not docs:
            raise ValueError("No documents could be loaded")
        
        # Use recursive splitter for better chunking
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=300,  # Smaller chunks for faster processing
            chunk_overlap=30,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
        split_docs = splitter.split_documents(docs)
        
        # Limit number of chunks to prevent memory issues
        if len(split_docs) > 200:
            split_docs = split_docs[:200]
        
        # Create vectorstore
        docsearch = FAISS.from_documents(split_docs, self._shared_embeddings)
        
        # Cache the vectorstore
        try:
            with open(cache_path, 'wb') as f:
                pickle.dump(docsearch, f)
        except:
            pass  # If caching fails, continue without cache
        
        return docsearch
    
    def _load_documents_optimized(self, file_paths: List[str]) -> List[Document]:
        """Load documents with size limits and error handling"""
        docs = []
        max_file_size = 5 * 1024 * 1024  # 5MB limit per file
        
        for path in file_paths:
            try:
                # Check file size
                if os.path.getsize(path) > max_file_size:
                    print(f"Skipping {path}: File too large")
                    continue
                
                ext = os.path.splitext(path)[1].lower()
                
                if ext == ".txt":
                    loader = TextLoader(path, encoding="utf-8")
                elif ext == ".pdf":
                    loader = PyPDFLoader(path)
                elif ext in (".docx", ".doc"):
                    loader = UnstructuredWordDocumentLoader(path)
                else:
                    continue
                
                file_docs = loader.load()
                
                # Limit content per document
                for doc in file_docs:
                    if len(doc.page_content) > 10000:  # Truncate very long documents
                        doc.page_content = doc.page_content[:10000] + "..."
                
                docs.extend(file_docs)
                
            except Exception as e:
                print(f"Error loading {path}: {e}")
                continue
        
        return docs
    
    def _get_cache_key(self, file_paths: List[str]) -> str:
        """Generate cache key based on file contents"""
        hasher = hashlib.md5()
        for path in sorted(file_paths):
            try:
                with open(path, 'rb') as f:
                    # Read first 1KB for hash (faster than full file)
                    hasher.update(f.read(1024))
            except:
                continue
        return hasher.hexdigest()[:16]
    
    def _setup_chain(self):
        """Setup the RAG chain"""
        template = """Based on the context below, answer the question concisely in 1-2 sentences.
If you don't know the answer, say "I don't know."

Context: {context}
Question: {question}
Answer:"""
        
        self.prompt = PromptTemplate(
            template=template, 
            input_variables=["context", "question"]
        )
        
        if self.docsearch:
            self.rag_chain = (
                {"context": self.docsearch.as_retriever(search_kwargs={"k": 2}), 
                 "question": RunnablePassthrough()}
                | self.prompt
                | self._shared_llm
                | StrOutputParser()
            )
        else:
            self.rag_chain = None
    
    async def ask_async(self, user_question: str) -> str:
        """Async version of ask method"""
        if not self.rag_chain:
            return "No documents loaded. Please upload documents first."
        
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor, 
                self._ask_sync, 
                user_question
            )
            return result
        except Exception as e:
            return f"Error processing question: {str(e)}"
    
    def _ask_sync(self, user_question: str) -> str:
        """Synchronous ask implementation"""
        try:
            raw = self.rag_chain.invoke(user_question)
            return raw.split("Answer:", 1)[-1].strip()
        except Exception:
            # Fallback to simple similarity search
            docs = self.docsearch.similarity_search(user_question, k=2)
            context = "\n".join([d.page_content[:200] for d in docs])  # Limit context
            
            formatted = self.prompt.format(context=context, question=user_question)
            raw = self._shared_llm(formatted)
            return raw.split("Answer:", 1)[-1].strip()
    
    def ask(self, user_question: str) -> str:
        """Synchronous ask method for backward compatibility"""
        return self._ask_sync(user_question)
    
    @classmethod
    def cleanup_cache(cls, max_age_hours: int = 24):
        """Clean up old cache files"""
        import time
        cache_dir = "/tmp"
        current_time = time.time()
        
        for filename in os.listdir(cache_dir):
            if filename.startswith("vectorstore_"):
                filepath = os.path.join(cache_dir, filename)
                if os.path.isfile(filepath):
                    file_age = current_time - os.path.getmtime(filepath)
                    if file_age > max_age_hours * 3600:
                        try:
                            os.remove(filepath)
                        except:
                            pass
