import os
from semantic_router import Route, SemanticRouter
from semantic_router.encoders import OpenAIEncoder

os.environ["OPENAI_API_KEY"] = "ollama"
os.environ["OPENAI_BASE_URL"] = "https://artful-microchemical-madie.ngrok-free.dev/v1"

try:
    encoder = OpenAIEncoder(
        name="deepseek-r1:latest"
    )
    route = Route(
        name="test",
        utterances=["hello"]
    )
    rl = SemanticRouter(encoder=encoder, routes=[route])
    result = rl("hello")
    print(f"Match: {result.name}")
except Exception as e:
    print(f"Error: {e}")
