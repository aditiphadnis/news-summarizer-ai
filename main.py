import openai
from dotenv import load_dotenv
import os
import logging
from datetime import datetime
import json
import requests
import time
import streamlit as st 
from tavily import TavilyClient


load_dotenv()

client = openai.OpenAI()
model = 'gpt-4o-mini'

news_api_key = os.getenv('NEWS_API_KEY')
tavily_api_key = os.getenv('TAVILY_API_KEY')
tavily_client = TavilyClient(api_key=tavily_api_key)



def get_news(topic):
    url = (f'https://newsapi.org/v2/everything?q={topic}&apiKey={news_api_key}&pageSize=5')

    try:
        response = requests.get(url)
        if response.status_code == 200:
            news = json.dumps(response.json(), indent=4)
            news_json = json.loads(news)
            data = news_json
            # Access all the fields in the json response
            status = data['status']
            total_results = data['totalResults']
            articles = data['articles']
            final_news = []
            #Loop through the articles
            for article in articles:
                source = article['source']
                author = article['author']
                title = article['title']
                description = article['description']
                content = article['content']
                url = article['url']
                title_description = f"""
                Title: {title}
                Author: {author}
                Source: {source}
                Description: {description}
                URL: {url}
                """
                final_news.append(title_description)
            return final_news
        else:
            return []
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news: {e}")
        return []

def tavily_search(query, search_depth="advanced"):
    """
    Perform a web search using Tavily API
    
    Args:
        query (str): The search query
        search_depth (str): The depth of search - "basic" or "deep"
        
    Returns:
        str: The search results as a formatted string
    """

    if not tavily_api_key:
        print("Tavily API key not found in environment variables")
        return "Error: Tavily API key not configured"

    try:
        search_result = tavily_client.search(
            query=query,
            search_depth=search_depth,
            max_results=5
        )
        if not search_result or "results" not in search_result:
            print("No results returned from Tavily search")
            return "No results found"
        
        # Format the results
        formatted_results = "Search Results:\n\n"
        
        for i, result in enumerate(search_result.get("results", [])):
            formatted_results += f"Result {i+1}:\n"
            formatted_results += f"Title: {result.get('title', 'No title')}\n"
            formatted_results += f"Content: {result.get('content', 'No content')}\n\n"        
        return formatted_results
    
    except Exception as e:
        error_message = f"Tavily search error: {str(e)}"
        print(error_message)
        return error_message
        print(f'Error happened during the API request: {str(e)}')
    

class AssistantManager:
    thread_id = 'thread_XlS39XKOBEh4Sm3fVJVJHdza'
    assistant_id = 'asst_pZqfPcv0hQ8Luh2ra03fDHYn'

    def __init__(self, model: str = model):
        self.client = client
        self.model = model
        self.assistant = None
        self.thread = None
        self.run = None
        self.summary = None

        #Retrieve existing assistant and thread id if ids are already created
        if AssistantManager.assistant_id:
            self.assistant = self.client.beta.assistants.retrieve(
                AssistantManager.assistant_id)
        if AssistantManager.thread_id:
            self.thread = self.client.beta.threads.retrieve(
                AssistantManager.thread_id)
            
    def create_assistant(self, name, instructions, tools):
        if not self.assistant:
            assistant_obj = self.client.beta.assistants.create(
                name = name,
                instructions = instructions,
                tools = tools,
                model = model
            )
            AssistantManager.assistant_id = assistant_obj.id
            self.assistant = assistant_obj
            print(f"AssisID:::: {self.assistant.id}")

    def create_thread(self):
        if not self.thread:
            thread_obj = client.beta.threads.create()
            AssistantManager.thread_id = thread_obj.id
            self.thread = thread_obj
            print(f"ThreadID:::: {self.thread.id}")

    def add_message_to_thread(self, role, content):
        if self.thread:
            self.client.beta.threads.messages.create(
                thread_id=self.thread.id,
                role = role,
                content = content
            )

    def run_assistant(self, instructions):
        if self.assistant and self.thread:
            self.run = self.client.beta.threads.runs.create(
                thread_id= self.thread.id,
                assistant_id= self.assistant.id,
                instructions = instructions
            )

    def process_messages(self):
        if self.thread:
            messages = self.client.beta.threads.messages.list(
                thread_id= self.thread.id
            )
            summary = []
            last_message = messages.data[0]
            role = last_message.role
            response = last_message.content[0].text.value
            summary.append(response)
            self.summary = "\n".join(summary)

            print(f"SUMMARY----->{role.capitalize()}: ===> {response}")

    def call_required_functions(self, required_actions):
        if not self.run:
            return 
        tool_outputs = []
        for action in required_actions["tool_calls"]:
            func_name = action["function"]["name"]
            arguments = json.loads(action["function"]["arguments"])

            try: 
                if func_name == "tavily_search":
                    query = arguments["query"]
                    search_depth = arguments.get("search_depth", "advanced")
                    print(f"Executing Tavily search for query: {query}")
                    output = tavily_search(query=query, search_depth=search_depth)
                    print(f"Tavily search output completed")
                    tool_outputs.append({"tool_call_id": action['id'],
                                         "output": output})
                    
                elif func_name == "get_news":
                    output = get_news(topic=arguments["topic"])
                    print(f"News API output received")
                    final_str = ''
                    for item in output:
                        final_str += "".join(item)

                    tool_outputs.append({"tool_call_id": action['id'],
                                        "output": final_str})
            except Exception as e:
                print(f"Error executing function: {func_name}: {str(e)}")
                tool_outputs.append({"tool_call_id": action['id'],
                                     "output": "Error executing function: {func_name}:" + str(e)})
                
        if tool_outputs:
            print("Submitting outputs back to the Assistant")
            self.client.beta.threads.runs.submit_tool_outputs(
                thread_id=self.thread.id,
                run_id=self.run.id,
                tool_outputs=tool_outputs
            )

                    
        

    # ++++ For streamlit +++++ 
    def get_summary(self):
        return self.summary

    def wait_for_completion(self):
        if self.thread and self.run:
            while True:
                time.sleep(5)
                run_status= self.client.beta.threads.runs.retrieve(
                    thread_id = self.thread.id,
                    run_id= self.run.id
                )
                print(f"RUN STATUS::: {run_status.model_dump_json(indent=4)}")

                if run_status.status == "completed":
                    self.process_messages()
                    break
                elif run_status.status == "requires_action":
                    print("FUNCTION CALLING NOW...")
                    self.call_required_functions(
                        required_actions= run_status.required_action.submit_tool_outputs.model_dump()
                    )
    # Run the steps
    def run_steps(self):
        run_steps = self.client.beta.threads.runs.steps.list(
            thread_id = self.thread.id,
            run_id= self.run.id
        )

        print(f" Run Steps::: {run_steps}")
        return run_steps


def main():
    # news = get_news("bitcoin")
    # print(news[0])
    manager = AssistantManager()
    # Streamlit

    st.title("News Summarizer")
    with st.form(key= "user_input_form"):
        instructions = st.text_input("Enter topic:")
        submit_button = st.form_submit_button(label= "Run Assistant")

        if submit_button:
            manager.create_assistant(name = "News and Search Assistant",
                                     instructions= """ You are a personal assistant that can summarize news articles 
                                     and search the web for information. Use the tavily_search function when you need 
                                     to find current information on the web, and use the get_news function when you 
                                     specifically need news articles on a topic.""",
                                     tools= [
                                            {
                                                "type": "function",
                                                "function": {
                                                    "name": "get_news",
                                                    "description": "Get the list of articles/news for the given topic",
                                                    "parameters": {
                                                        "type": "object",
                                                        "properties": {
                                                            "topic": {
                                                                "type": "string",
                                                                "description": "The topic for the news, e.g. bitcoin",
                                                            }
                                                        },
                                                        "required": ["topic"],
                                                    },
                                                },
                                            },
                                            {
                                                "type": "function",
                                                "function": {
                                                    "name": "tavily_search",
                                                    "description": "Search the web for current information on a given topic",
                                                    "parameters": {
                                                        "type": "object",
                                                        "properties": {
                                                            "query": {
                                                                "type": "string",
                                                                "description": "The search query to look up on the web",
                                                            },
                                                            "search_depth": {
                                                                "type": "string",
                                                                "enum": ["basic", "deep"],
                                                                "description": "The depth of search - basic is faster, deep is more comprehensive",
                                                            }
                                                        },
                                                        "required": ["query"],
                                                    },
                                                },
                                            }
                                        ],
                                    )
            manager.create_thread()

            #Add message to thread 
            manager.add_message_to_thread(
                role="user",
                content= f'Summarize content on this topic {instructions} '
            )
            manager.run_assistant(instructions= "Summarize the news")

            # Wait for completion

            manager.wait_for_completion()

            summary = manager.get_summary()

            st.write(summary)
            st.text("Run Steps: ")
            st.code(manager.run_steps(),line_numbers=True)
            
            
if __name__ == '__main__':
    main()