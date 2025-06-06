import os
from dotenv import load_dotenv

# LangChain imports (updated to avoid deprecation warnings)
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS  # Using FAISS instead of Pinecone
from langchain_community.llms import HuggingFaceHub
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


class ChatBot:
    def __init__(self):
        # 1) Load API keys from .env
        load_dotenv()
        hf_key = os.getenv("HUGGINGFACE_API_KEY")
        if not hf_key:
            raise ValueError("Set HUGGINGFACE_API_KEY in .env")

        # 2) Load & split the document(s)
        try:
            loader = TextLoader(os.path.join("data", "horoscope.txt"), encoding='utf-8')
            documents = loader.load()
            if not documents or not documents[0].page_content.strip():
                raise ValueError("No valid content in 'data/horoscope.txt'")

            text_splitter = CharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50,
                separator="\n"
            )
            docs = text_splitter.split_documents(documents)
            if not docs:
                docs = documents

        except Exception:
            from langchain.schema import Document
            docs = [
                Document(page_content="Aries: You will have good luck today. The stars align in your favor for success.", metadata={"source": "sample", "sign": "aries"}),
                Document(page_content="Taurus: Be patient today. Good things come to those who wait. Your persistence will pay off.", metadata={"source": "sample", "sign": "taurus"}),
                Document(page_content="Gemini: Communication is key today. Reach out to loved ones and express your feelings.", metadata={"source": "sample", "sign": "gemini"})
            ]

        # 3) Create HuggingFace embeddings
        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

        # 4) Create FAISS vectorstore
        texts = [doc.page_content for doc in docs]
        metadatas = [doc.metadata for doc in docs]
        self.docsearch = FAISS.from_texts(texts=texts, embedding=embeddings, metadatas=metadatas)

        # 5) Set up the HuggingFaceHub LLM
        repo_id = "mistralai/Mixtral-8x7B-Instruct-v0.1"
        self.llm = HuggingFaceHub(
            repo_id=repo_id,
            model_kwargs={"temperature": 0.8, "top_k": 50},
            huggingfacehub_api_token=hf_key
        )

        # 6) Prepare the prompt template. Notice the extra instruction to return only the answer.
        template = """
You are a fortune teller. These Humans will ask you questions about their life.
Use the following piece of context to answer the question.
If you don't know the answer, just say you don't know.
Keep the answer within 2 sentences.
Return ONLY the two‐sentence answer (do NOT include “Context:” or repeat the question).

Context:
{context}

Question: {question}
Answer:"""

        self.prompt = PromptTemplate(template=template, input_variables=["context", "question"])

        # 7) Build the RAG chain
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
            # Fallback: manual retrieval + LLM call
            docs = self.docsearch.similarity_search(user_question, k=3)
            context = "\n".join([doc.page_content for doc in docs])
            formatted = self.prompt.format(context=context, question=user_question)
            raw = self.llm(formatted)

        # If the model echoed the prompt, split on "Answer:" and return only what follows
        if "Answer:" in raw:
            return raw.split("Answer:", 1)[1].strip()
        else:
            return raw.strip()


if __name__ == "__main__":
    bot = ChatBot()
    query = input("Ask me anything: ")
    answer = bot.ask(query)
    print(answer)
