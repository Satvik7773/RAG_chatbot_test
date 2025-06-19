import os
from dotenv import load_dotenv

# LangChain loaders and utilities
from langchain_community.document_loaders import UnstructuredWordDocumentLoader
from langchain_community.document_loaders import TextLoader
from langchain_community.document_loaders import PyPDFLoader   
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.llms import HuggingFaceHub
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain.schema import Document


class ChatBot:
    def __init__(self, file_paths: list[str] | None = None):
        # 1) Load API key
        load_dotenv()
        hf_key = os.getenv("HUGGINGFACE_API_KEY")
        if not hf_key:
            raise ValueError("Set HUGGINGFACE_API_KEY in .env")

        # 2) Load & split the document(s)
        docs: list[Document] = []
        if file_paths:
            for path in file_paths:
                ext = os.path.splitext(path)[1].lower()
                if ext == ".txt":
                    loader = TextLoader(path, encoding="utf-8")
                elif ext == ".pdf":
                    loader = PyPDFLoader(path)
                elif ext in (".docx", ".doc"):
                    loader = UnstructuredWordDocumentLoader(path)
                else:
                    continue
                docs.extend(loader.load())

        if not docs:
            docs = [
                Document(page_content="Aries: You will have good luck today. The stars align in your favor for success.", metadata={"sign": "aries"}),
                Document(page_content="Taurus: Be patient today. Good things come to those who wait. Your persistence will pay off.", metadata={"sign": "taurus"}),
                Document(page_content="Gemini: Communication is key today. Reach out to loved ones and express your feelings.", metadata={"sign": "gemini"})
            ]

        splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50, separator="\n")
        split_docs = splitter.split_documents(docs)

        # 3) Create embeddings & 4) build FAISS vectorstore
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.docsearch = FAISS.from_documents(split_docs, embeddings)

        # 5) Configure the LLM
        repo_id = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self.llm = HuggingFaceHub(
            repo_id=repo_id,
            model_kwargs={"temperature": 0.8, "top_k": 50},
            huggingfacehub_api_token=hf_key
        )

        # 6) Prompt template
        template = """
You are a fortune teller. These Humans will ask you questions about their life.
Use the following piece of context to answer the question.
If you don't know the answer, just say you don't know.
Keep the answer within 2 sentences.
Return ONLY the two‐sentence answer.

Context:
{context}

Question: {question}
Answer:"""
        self.prompt = PromptTemplate(template=template, input_variables=["context", "question"])

        self.rag_chain = (
            {"context": self.docsearch.as_retriever(), "question": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

    def ask(self, user_question: str) -> str:
        try:
            raw = self.rag_chain.invoke(user_question)
        except Exception:
            docs = self.docsearch.similarity_search(user_question, k=3)
            context = "\n".join([d.page_content for d in docs])
            formatted = self.prompt.format(context=context, question=user_question)
            raw = self.llm(formatted)

        # Clean up output
        return raw.split("Answer:", 1)[-1].strip()
