from langchain_groq import ChatGroq
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

def llm_pick(level: str):
    """
    Function to pick the appropriate LLM based on the level of complexity.

    Args:
        level (str): The level of complexity ('low', 'medium', 'high').

    Returns:
        str: The name of the selected LLM.
    """

    if level.lower() == 'low':
        llm = ChatGroq(model="qwen/qwen3.8-27b" , temperature=0)
    elif level.lower() == 'medium':
        llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    elif level.lower() == 'high':
        llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
    else:
        raise ValueError("Invalid level. Choose from 'low', 'medium', or 'high'.")
    
    return llm

llm_obj= llm_pick("low")
print(llm_obj.invoke("What is the Capital of France?"))