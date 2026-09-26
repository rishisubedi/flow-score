from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

def get_llm(llm_config: dict):
    """
    Dynamically returns an LLM instance based on the tenant's BYOK config.
    """
    provider = llm_config.get("provider", "openai")
    api_key = llm_config.get("api_key")
    
    if provider == "gemini":
        return ChatGoogleGenerativeAI(
            model="gemini-3.8-flash",
            temperature=0.0,
            google_api_key=api_key
        )
    else:
        # Default to OpenAI
        return ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.0,
            api_key=api_key
        )
