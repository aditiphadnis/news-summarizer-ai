# The News Summarizer App  

This app is built using OpenAI’s **Assistant API**, which allows us to pass tools and function calls within our assistant (still in beta). It leverages **NewsAPI** from [newsapi.org](https://newsapi.org) to fetch the latest news. If the function call fails, it seamlessly switches to the **Tavily Search API** to ensure uninterrupted access to news updates.  

As I am not expecting many users to use this app at the same time, I have hardcoded a single `ThreadId` under the `AssistantId`. However, in production applications, we might need to consider a more robust architecture.  

## Want a quick, AI-powered news summary? 📰  

You can check out the app here 👉 **[News Summarizer](https://news-summarize.streamlit.app/)** (hosted on Streamlit).  






