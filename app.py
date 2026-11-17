import os
import streamlit as st
import pandas as pd
from agents.data_agent import data_agent
from langchain_core.messages import HumanMessage

# Page Configuration
st.set_page_config(
    page_title="AI Data Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .main-header { font-size: 2.2rem; font-weight: 700; color: #1E88E5; margin-bottom: 0.2rem; }
    .sub-header { color: #666; margin-bottom: 2rem; }
    .stCodeBlock { border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🤖 Agentic AI Data Platform</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Natural Language to SQL Queries & Automated ETL Workflows</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ System Status")
    
    # Check Environment
    groq_ready = bool(os.getenv("GROQ_API_KEY"))
    db_ready = bool(os.getenv("DATABASE_URL") or os.getenv("host"))
    
    st.write(f"**Groq API:** {'🟢 Connected' if groq_ready else '🔴 Missing Key'}")
    st.write(f"**Supabase DB:** {'🟢 Configured' if db_ready else '🟡 Unconfigured'}")
    
    st.divider()
    
    st.header("💡 Example Queries")
    st.caption("Click any example to paste it into the prompt:")
    
    examples = [
        "Show me the top 5 users who took the most rides",
        "What are the different types of payment methods and how many transactions for each?",
        "What is the average ride fare and distance for completed rides?",
        "Extract data from API 'https://pokeapi.co/api/v2/pokemon' and save to data/extract in csv format"
    ]
    
    for ex in examples:
        if st.button(ex, key=ex):
            st.session_state["pending_prompt"] = ex

    st.divider()
    if st.button("🗑️ Clear Chat History", use_container_width=True):
        st.session_state["messages"] = []
        st.rerun()

# -----------------------------------------------------------------------------
# CHAT SESSION STATE
# -----------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display conversation history
for msg in st.session_state["messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        
        # Display supplementary details if available
        if "details" in msg:
            details = msg["details"]
            route = details.get("route", "")
            
            if route == "sql":
                with st.expander("🔍 View SQL Analysis Breakdown", expanded=False):
                    if details.get("sql"):
                        st.markdown("**Generated SQL:**")
                        st.code(details["sql"], language="sql")
                    if details.get("safety"):
                        st.markdown(f"**Safety Status:** {details['safety']}")
                    if details.get("raw_results"):
                        st.markdown("**Database Execution Results:**")
                        st.code(details["raw_results"], language="text")
            
            elif route == "etl":
                with st.expander("⚙️ View ETL Execution Details", expanded=False):
                    st.write("ETL pipeline executed using Pandas / REST tools.")
                    # Show extracted files if any exist
                    extract_path = os.path.join("data", "extract", "extracted_data.csv")
                    if os.path.exists(extract_path):
                        st.success(f"File created: `{extract_path}`")
                        try:
                            df = pd.read_csv(extract_path)
                            st.dataframe(df.head(5))
                        except Exception:
                            pass

# -----------------------------------------------------------------------------
# USER INPUT HANDLING
# -----------------------------------------------------------------------------
prompt = st.chat_input("Ask a question about your database or request an ETL extraction...")

# Handle click from sidebar examples
if "pending_prompt" in st.session_state and st.session_state["pending_prompt"]:
    prompt = st.session_state.pop("pending_prompt")

if prompt:
    # 1. Render User Message
    st.session_state["messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Invoke Data Agent
    with st.chat_message("assistant"):
        with st.spinner("Analyzing request and orchestrating sub-agents..."):
            try:
                response = data_agent.invoke({
                    "messages": [HumanMessage(content=prompt)],
                    "route_response": ""
                })
                
                route = response.get("route_response", "unknown")
                last_msg = response["messages"][-1]
                
                final_answer = ""
                details = {"route": route}

                # Extract details based on agent route
                if route == "sql":
                    # SQL agent returns state dict with final_answer & generated_sql_query
                    if isinstance(last_msg, dict):
                        final_answer = last_msg.get("final_answer", "")
                        details["sql"] = last_msg.get("generated_sql_query", "")
                        details["safety"] = f"{last_msg.get('is_safe', 'Unknown')} - {last_msg.get('comments', '')}"
                        details["raw_results"] = last_msg.get("sql_query_execution_result", "")
                    elif hasattr(last_msg, "content"):
                        final_answer = last_msg.content
                    
                    st.markdown(f"**[SQL Analyst Agent]**\n\n{final_answer}")
                    
                    with st.expander("🔍 View SQL Analysis Breakdown", expanded=True):
                        if details.get("sql"):
                            st.markdown("**Generated SQL:**")
                            st.code(details["sql"], language="sql")
                        if details.get("safety"):
                            st.markdown(f"**Safety Status:** {details['safety']}")
                        if details.get("raw_results"):
                            st.markdown("**Database Execution Results:**")
                            st.code(details["raw_results"], language="text")

                elif route == "etl":
                    # ETL agent returns messages
                    if isinstance(last_msg, dict) and "messages" in last_msg:
                        final_answer = last_msg["messages"][-1].content
                    elif hasattr(last_msg, "content"):
                        final_answer = last_msg.content
                    else:
                        final_answer = str(last_msg)

                    st.markdown(f"**[ETL Analyst Agent]**\n\n{final_answer}")
                    
                    extract_path = os.path.join("data", "extract", "extracted_data.csv")
                    if os.path.exists(extract_path):
                        with st.expander("📁 Inspect Extracted CSV Data", expanded=True):
                            try:
                                df = pd.read_csv(extract_path)
                                st.dataframe(df)
                            except Exception as e:
                                st.write(f"Could not preview CSV: {e}")

                # Save assistant response to session state
                st.session_state["messages"].append({
                    "role": "assistant",
                    "content": final_answer,
                    "details": details
                })

            except Exception as err:
                st.error(f"Execution Error: {err}")