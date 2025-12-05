from langgraph.graph import StateGraph
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, ToolMessage
import json
from tools import (
    get_repo_info,
    get_repo_languages,
    get_repo_commits,
    get_repo_branches,
    get_repo_contributors,
    list_repo_files,
    get_file_content
)

class State(BaseModel):
    messages: list

# Initialize the LLM with tools bound
llm = ChatOpenAI(model="gpt-4o-mini").bind_tools([
    get_repo_info,
    get_repo_languages,
    get_repo_commits,
    get_repo_branches,
    get_repo_contributors,
    list_repo_files,
    get_file_content
])

# Map tool names to functions
TOOLS = {
    "get_repo_info": get_repo_info,
    "get_repo_languages": get_repo_languages,
    "get_repo_commits": get_repo_commits,
    "get_repo_branches": get_repo_branches,
    "get_repo_contributors": get_repo_contributors,
    "list_repo_files": list_repo_files,
    "get_file_content": get_file_content,
}

def execute_tools(state: State):
    """Manually execute tools and preserve message history"""
    print(f"\nTOOL EXECUTION - Processing {len(state.messages)} messages")
    
    # Get the last AI message with tool calls
    last_message = state.messages[-1]
    
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        print("No tool calls found in last message")
        return state
    
    # Execute each tool call
    tool_results = []
    for tool_call in last_message.tool_calls:
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        tool_id = tool_call["id"]
        
        print(f"  Executing: {tool_name}({list(tool_args.keys())})")
        
        try:
            # Get the tool function
            tool_func = TOOLS[tool_name]
            
            # Call using .invoke() for StructuredTool objects
            result = tool_func.invoke(tool_args)
            
            # Convert result to JSON string for better readability
            if isinstance(result, (dict, list)):
                content = json.dumps(result, indent=2)
            else:
                content = str(result)
            
            # Create a ToolMessage for this result
            tool_message = ToolMessage(
                content=content,
                tool_call_id=tool_id,
                name=tool_name
            )
            tool_results.append(tool_message)
            print(f"    ✓ Success - returned {len(content)} chars")
        except Exception as e:
            print(f"    ✗ Error: {str(e)}")
            tool_message = ToolMessage(
                content=f"Error executing {tool_name}: {str(e)}",
                tool_call_id=tool_id,
                name=tool_name
            )
            tool_results.append(tool_message)
    
    # IMPORTANT: Append tool messages to preserve history
    new_messages = state.messages + tool_results
    
    print(f"Tool execution complete. Total messages now: {len(new_messages)}")
    
    return {"messages": new_messages}

def agent_node(state: State):
    """Call the LLM with accumulated messages"""
    print(f"\n{'='*60}")
    print(f"AGENT NODE - Current messages: {len(state.messages)}")
    for i, msg in enumerate(state.messages):
        msg_type = type(msg).__name__
        has_calls = hasattr(msg, 'tool_calls') and bool(msg.tool_calls)
        print(f"  [{i}] {msg_type} (tool_calls: {has_calls})")
    print(f"{'='*60}")
    
    # Invoke LLM with full message history
    ai_msg = llm.invoke(state.messages)
    print(f"AI Message created with {len(ai_msg.tool_calls) if hasattr(ai_msg, 'tool_calls') else 0} tool calls")
    
    # Return updated state - append AI message
    new_messages = state.messages + [ai_msg]
    print(f"Returning {len(new_messages)} total messages")
    return {"messages": new_messages}

def tool_condition(state: State):
    """Determine if we should call tools or end"""
    last = state.messages[-1]
    
    # Check if the last message is an AI message with tool calls
    if hasattr(last, "tool_calls") and last.tool_calls:
        print(f"Tool condition: routing to tools ({len(last.tool_calls)} calls)")
        return "tools"
    
    print("Tool condition: routing to end")
    return "end"

# Build the graph
graph = StateGraph(State)

# Add nodes
graph.add_node("agent", agent_node)
graph.add_node("tools", execute_tools)

# Set entry point
graph.set_entry_point("agent")

# Add conditional edges from agent
graph.add_conditional_edges(
    "agent",
    tool_condition,
    {
        "tools": "tools",
        "end": "__end__"
    }
)

# Add edge from tools back to agent
graph.add_edge("tools", "agent")

# Compile the graph
app = graph.compile()


def get_final_ai_response(response):
    """Extract the final AI message that contains the summary"""
    for msg in reversed(response["messages"]):
        if type(msg).__name__ == "AIMessage" and hasattr(msg, 'content'):
            return msg.content
    return "(No AI response found)"


def run_analysis(repo_url):
    """Run initial repository analysis"""
    response = app.invoke({
        "messages": [
            HumanMessage(
                content=f"""
                Analyze {repo_url} and give me a comprehensive summary. 
                
                Make sure to:
                1. Get basic repository information
                2. Check the programming languages used
                3. Review recent commits
                4. Look at the branches
                5. See who the main contributors are
                6. Browse the repository structure and list files
                
                After listing files, I will ask you to analyze specific files.
                """
            )
        ]
    })
    
    print("\n" + "="*80)
    print("=== INITIAL REPOSITORY ANALYSIS ===")
    print("="*80)
    final_summary = get_final_ai_response(response)
    print(final_summary)
    
    return response


def interactive_file_explorer(initial_response, repo_url):
    """Interactive chatbot to explore specific files"""
    messages = initial_response["messages"].copy()
    
    print("\n" + "="*80)
    print("=== INTERACTIVE FILE EXPLORER ===")
    print("="*80)
    print("\nNow you can ask me to analyze specific files from the repository.")
    print("Examples:")
    print("  - Read README.md")
    print("  - Show me the pyproject.toml")
    print("  - Analyze main.py in the fastapi folder")
    print("  - What's in requirements.txt")
    print("  - Type 'exit' to quit\n")
    
    while True:
        user_input = input("You: ").strip()
        
        if user_input.lower() == 'exit':
            print("Thanks for exploring! Goodbye!")
            break
        
        if not user_input:
            continue
        
        # Add user message to conversation
        messages.append(HumanMessage(content=user_input))
        
        # Run the agent with the updated message history
        response = app.invoke({"messages": messages})
        
        # Get the final AI response
        final_response = get_final_ai_response(response)
        
        print(f"\nAssistant: {final_response}\n")
        
        # Update messages for next iteration
        messages = response["messages"]


if __name__ == "__main__":
    print("="*80)
    print("INTERACTIVE GITHUB REPOSITORY ANALYZER")
    print("="*80)
    
    # Get repository URL from user
    repo_url = input("\nEnter GitHub repository URL (e.g., https://github.com/tiangolo/fastapi): ").strip()
    
    if not repo_url:
        repo_url = "https://github.com/tiangolo/fastapi"
        print(f"Using default repository: {repo_url}")
    
    # Run initial analysis
    initial_response = run_analysis(repo_url)
    
    # Start interactive file explorer
    interactive_file_explorer(initial_response, repo_url)