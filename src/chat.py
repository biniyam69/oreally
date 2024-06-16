from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.pydantic_v1 import BaseModel
import uuid, time
from typing import List
from langchain_core.messages import HumanMessage

user_background = {"name": str, "age": int, "favorite_party": str}

template = f"""Your job is to ask the user atleast 20 questions about their political views and determine who they should vote for.

You have to ask one question at a time. Only 1 question at a time.
"""

llm = ChatOpenAI(temperature=0)

def get_messages_info(messages):
    return [SystemMessage(content=template)] + messages


class PromptInstructions(BaseModel):
    """Instructions on how to prompt the LLM."""

    objective: str
    variables: List[str]
    constraints: List[str]
    requirements: List[str]
    
    
llm_with_tool = llm.bind_tools([PromptInstructions])
chain = get_messages_info | llm_with_tool

def _is_tool_call(msg):
    return hasattr(msg, "additional_kwargs") and "tool_calls" in msg.additional_kwargs


# New system prompt
prompt_system = """Based on the following requirements:

{reqs}"""


def get_prompt_messages(messages):
    tool_call = None
    other_msgs = []
    for m in messages:
        if _is_tool_call(m):
            tool_call = m.additional_kwargs["tool_calls"][0]["function"]["arguments"]
        elif tool_call is not None:
            other_msgs.append(m)
    return [SystemMessage(content=prompt_system.format(reqs=tool_call))] + other_msgs

prompt_gen_chain = get_prompt_messages | llm

def get_state(messages):
    if _is_tool_call(messages[-1]):
        return "prompt"
    elif not isinstance(messages[-1], HumanMessage):
        return END
    for m in messages:
        if _is_tool_call(m):
            return "prompt"
    return "info"

"""Graph Section"""

from langgraph.graph import MessageGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

memory = SqliteSaver.from_conn_string(":memory:")

nodes = {k: k for k in ["info", "prompt", END]}
workflow = MessageGraph()
workflow.add_node("info", chain)
workflow.add_node("prompt", prompt_gen_chain)
workflow.add_conditional_edges("info", get_state, nodes)
workflow.add_conditional_edges("prompt", get_state, nodes)
workflow.set_entry_point("info")
graph = workflow.compile(checkpointer=memory)


config = {"configurable": {"thread_id": str(uuid.uuid4())}}
def chatbot_conversation(user_input):
    if user_input.lower() in {"q", "quit"}:
        return "Byebye"
    else:
        response = []
        for output in graph.stream([HumanMessage(content=user_input)], config=config):
            if "__end__" in output:
                continue
            for key, value in output.items():
                response.append(value.content)
        
        response_text = "\n---\n".join(response)
        
        return response_text
    
if __name__ == "__main__":
    print("Welcome to the chatbot! Type 'quit' or 'q' to exit.")
    while True:
        user_input = input("You: ")
        ##user_message = create_user_message(user_input)
        response = chatbot_conversation(user_input=user_input)
        print("Bot:", response)
        if "goodbye" in response.lower():
            #User.objects.filter(id=user_id).update(chat_status='Completed')
            break