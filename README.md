ChatBot with LangChain, HuggingFace, and FAISS

Overview

This project implements a simple ChatBot that uses Retrieval-Augmented Generation (RAG) to answer questions based on a small “horoscope” text file. Internally, it uses:

HuggingFaceEmbeddings: To convert text chunks into numerical vectors (embeddings) that capture semantic meaning.

FAISS (Facebook AI Similarity Search): A vector database to store those embeddings and perform fast nearest‐neighbor searches (semantic retrieval).

HuggingFaceHub LLM: A language model (Mixtral-8x7B-Instruct) hosted on Hugging Face, which takes a short prompt (with retrieved context) and generates an answer.

LangChain: A Python library that glues together document loading, splitting, embedding, vector stores, prompt templating, and LLM calls into a coherent “chain.”

