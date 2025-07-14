from langchain_groq import ChatGroq
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_core.runnables import RunnableMap, RunnableLambda
from typing import List
from langchain_core.documents import Document
from chroma_utils import vectore_store
import os 

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

retriever=vectore_store.as_retriever()
output_parser= StrOutputParser()

# Set up prompts and chains
contextualize_q_system_prompt = (
    "Given a chat history and the latest user question "
    "which might reference context in the chat history, "
    "formulate a standalone question which can be understood "
    "without the chat history. Do NOT answer the question, "
    "just reformulate it if needed and otherwise return it as is."
)

#contextualize prompt
contextualize_prompt= ChatPromptTemplate.from_messages([
                    ("system", contextualize_q_system_prompt),
                    MessagesPlaceholder("chat_history"),
                    ("human", "{input}")
                ])

qa_prompt = ChatPromptTemplate.from_messages([
            ("system", "you are an helpful AI Assistant who always response respectfully. Use the following context to answer the user's question."),
            ("system", "context: {context}"),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])

def get_rag_chain(model="llama-3.1-8b-instant"):
    # import getpass
    # import os
    # if "GROQ_API_KEY" not in os.environ:
    #     os.environ["GROQ_API_KEY"] = getpass.getpass("Enter your Groq API key: ")

    llm= ChatGroq(model=model,
                  groq_api_key=GROQ_API_KEY)
    history_aware_retriever =create_history_aware_retriever(llm, retriever, contextualize_prompt)
    qa_chain= create_stuff_documents_chain(llm, qa_prompt)
    rag_chain= create_retrieval_chain(history_aware_retriever, qa_chain)
     # Step 4: Wrap with a RunnableMap to extract citations
    # rag_with_citations = RunnableMap({
    #     "answer": rag_chain,
    #     "documents": RunnableLambda(lambda x: history_aware_retriever.invoke(x)),
    # })
    # print("Answer with Citations : ", rag_with_citations)
    return rag_chain