from openai import OpenAI

client = OpenAI(
    base_url="https://artful-microchemical-madie.ngrok-free.dev/v1",
    api_key="ollama",
)

try:
    response = client.chat.completions.create(
        model="deepseek-r1:latest",
        messages=[{"role": "user", "content": "I bought coffee for $5"}],
        tools=[{
            "type": "function",
            "function": {
                "name": "insert_transaction",
                "parameters": {
                    "type": "object",
                    "properties": {"amount": {"type": "number"}, "merchant": {"type": "string"}},
                    "required": ["amount", "merchant"]
                }
            }
        }]
    )
    print("Success:")
    print(response.choices[0].message)
except Exception as e:
    print(f"Error: {e}")
