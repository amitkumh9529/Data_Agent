import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()


def pick_llm(level: str):
    """
    Selects the appropriate Groq LLM based on task complexity level.

    Args:
        level (str): The level of complexity ('low', 'medium', 'high', 'claude').

    Returns:
        ChatGroq: An instantiated ChatGroq model object.
    """
    lvl = level.lower().strip()

    if lvl == "low":
        # Fast, cost-efficient model for simple curation, rephrasing, and formatting
        llm = ChatGroq(model="qwen/qwen3.8-27b", temperature=0)
    elif lvl == "medium":
        # Balanced model for SQL generation and safety judging
        llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)
    elif lvl in ("high", "claude"):
        # Highest capacity model for routing, tool binding, and complex ETL reasoning
        llm = ChatGroq(model="openai/gpt-oss-120b", temperature=0)
    else:
        # Fallback to balanced model
        llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0)

    return llm


# Alias for backward compatibility
llm_pick = pick_llm


if __name__ == "__main__":
    llm_obj = pick_llm("low")
    print("Testing low tier:", llm_obj.invoke("What is the capital of France?").content)
