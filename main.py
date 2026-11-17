import sys
from agents.data_agent import data_agent
from langchain_core.messages import HumanMessage


def run_query(query: str):
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")

    response = data_agent.invoke(
        {
            "messages": [HumanMessage(content=query)],
            "route_response": ""
        }
    )

    route = response.get("route_response", "unknown")
    print(f"\n[Routed To]: {route.upper()} Analyst Agent")

    last_message = response["messages"][-1]
    if hasattr(last_message, "content"):
        output = last_message.content
    elif isinstance(last_message, dict) and "final_answer" in last_message:
        output = last_message["final_answer"]
    else:
        output = str(last_message)

    print(f"\n[Agent Answer]:\n{output}")
    print(f"{'='*60}\n")
    return response


if __name__ == "__main__":
    if len(sys.argv) > 1:
        user_query = " ".join(sys.argv[1:])
        run_query(user_query)
    else:
        # Example ETL operation
        sample_etl = "Extract data from API 'https://pokeapi.co/api/v2/pokemon' and save to data/extract in csv format"
        run_query(sample_etl)

        # Example SQL operation (requires Supabase database configured & seeded)
        sample_sql = "What are the different types of payment methods available in the database?"
        run_query(sample_sql)
