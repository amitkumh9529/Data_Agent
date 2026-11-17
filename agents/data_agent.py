import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.llm_pick import pick_llm
from Models.schema import RouterSchema, DataAgentSchema
from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END
from agents.etl_analyst import etl_analyst
from agents.sql_analyst import sql_analyst


llm = pick_llm("high")
llm_router = llm.with_structured_output(RouterSchema)


# ---------------------------- DATA AGENT GRAPH ---------------------------- #

def router_node(state: DataAgentSchema):
    message = state.messages[-1].content
    prompt = f"""
    You are an intelligent request router for a data analytics platform.
    Analyze the user's request and classify whether it requires:
    - 'sql': Querying an existing relational database (PostgreSQL) using SQL.
    - 'etl': Extracting data from APIs/web sources or transforming files (CSV/JSON/Parquet) using Pandas.

    User Request: {message}
    """
    route_response_dict = llm_router.invoke(prompt).model_dump()
    route_response = route_response_dict['answer']
    state.route_response = route_response
    return state


def etl_node(state: DataAgentSchema):
    message = state.messages[-1].content
    response = etl_analyst.invoke(
        {"messages": [HumanMessage(content=f"{message}")]}
    )
    state.messages = state.messages + [response]
    return state


def sql_node(state: DataAgentSchema):
    message = state.messages[-1].content
    input_schema = {
        "messages": [],
        "user_question": f"{message}",
        "curated_ques": "",
        "prompt_query_context": "",
        "generated_sql_query": "",
        "is_safe": "No",
        "comments": "",
        "sql_query_execution_result": "",
        "final_answer": ""
    }
    response = sql_analyst.invoke(input_schema)
    state.messages = state.messages + [response]
    return state


data_agent_graph = StateGraph(DataAgentSchema)

data_agent_graph.add_node("router_node", router_node)
data_agent_graph.add_node("etl_node", etl_node)
data_agent_graph.add_node("sql_node", sql_node)

data_agent_graph.add_edge(START, "router_node")


def route_edge(state: DataAgentSchema) -> str:
    if state.route_response == "sql":
        return "sql_node"
    elif state.route_response == "etl":
        return "etl_node"
    else:
        raise ValueError(f"Invalid route response: {state.route_response}")


data_agent_graph.add_conditional_edges(
    "router_node",
    route_edge,
    {
        "sql_node": "sql_node",
        "etl_node": "etl_node"
    }
)

data_agent = data_agent_graph.compile()


if __name__ == "__main__":
    try:
        # from IPython.display import Image
        # img = Image(data_agent.get_graph().draw_mermaid_png())
        png_bytes = data_agent.get_graph().draw_mermaid_png()
        with open("data_agent_graph.png", "wb") as f:
            f.write(png_bytes)
        print("Graph image saved to data_agent_graph.png")
    except Exception as e:
        print(f"Graph image generation skipped: {e}")

    sample_query = "I want to extract data from API 'https://pokeapi.co/api/v2/pokemon' and save to data/extract in csv format"
    response = data_agent.invoke({
        "messages": [HumanMessage(content=sample_query)],
        "route_response": ""
    })
    print("Agent Response:\n", response)
