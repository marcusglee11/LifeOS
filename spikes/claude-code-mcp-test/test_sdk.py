import anthropic
import os

client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY"),
    base_url=os.environ.get("ANTHROPIC_BASE_URL")
)

print(f"Testing endpoint: {client.base_url}")
print(f"Model: minimax-m2.1-free")

response = client.messages.create(
    model="minimax-m2.1-free",
    max_tokens=100,
    messages=[{"role": "user", "content": "Say OK and nothing else."}]
)

print(f"\nResponse blocks:")
for block in response.content:
    print(f"  Type: {block.type}")
    if hasattr(block, 'text'):
        print(f"  Text: {block.text}")
    elif hasattr(block, 'thinking'):
        print(f"  Thinking: {block.thinking[:100]}...")
print(f"\nTokens: {response.usage}")
