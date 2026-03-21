# Example client for testing vLLM Service

from openai import OpenAI
import os

# Configuration
BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
API_KEY = os.environ.get("VLLM_API_KEY", "your-api-key")
MODEL = os.environ.get("VLLM_MODEL_NAME", "Qwen/Qwen2.5-7B-Instruct")


def test_health():
    """Test health endpoint."""
    import httpx
    response = httpx.get(f"{BASE_URL.replace('/v1', '')}/health")
    print(f"Health check: {response.json()}")
    return response.status_code == 200


def test_list_models(client):
    """Test list models endpoint."""
    models = client.models.list()
    print(f"Available models: {[m.id for m in models.data]}")
    return models


def test_chat_completion(client):
    """Test chat completion."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'Hello, World!' and nothing else."},
        ],
        temperature=0.7,
        max_tokens=50,
    )
    print(f"Response: {response.choices[0].message.content}")
    return response


def test_chat_streaming(client):
    """Test chat completion with streaming."""
    print("Streaming response: ", end="")
    stream = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "user", "content": "Count from 1 to 5."},
        ],
        stream=True,
        max_tokens=50,
    )
    
    full_response = ""
    for chunk in stream:
        if chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            print(content, end="", flush=True)
            full_response += content
    print()
    return full_response


def test_completion(client):
    """Test text completion."""
    response = client.completions.create(
        model=MODEL,
        prompt="The capital of France is",
        max_tokens=10,
    )
    print(f"Completion: {response.choices[0].text}")
    return response


def test_tokenize():
    """Test tokenize endpoint."""
    import httpx
    response = httpx.post(
        f"{BASE_URL.replace('/v1', '')}/tokenize",
        json={"text": "Hello, world!"},
        headers={"Authorization": f"Bearer {API_KEY}"},
    )
    print(f"Tokenize result: {response.json()}")
    return response.json()


def test_vllm_params(client):
    """Test vLLM-specific parameters."""
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": "Hello"}],
        extra_body={
            "top_k": 50,
            "repetition_penalty": 1.2,
        },
        max_tokens=20,
    )
    print(f"Response with vLLM params: {response.choices[0].message.content}")
    return response


def main():
    """Run all tests."""
    print("=== vLLM Service Client Test ===\n")
    
    # Initialize client
    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
    )
    
    # Run tests
    tests = [
        ("Health Check", lambda: test_health()),
        ("List Models", lambda: test_list_models(client)),
        ("Chat Completion", lambda: test_chat_completion(client)),
        ("Chat Streaming", lambda: test_chat_streaming(client)),
        ("Text Completion", lambda: test_completion(client)),
        ("Tokenize", lambda: test_tokenize()),
        ("vLLM Parameters", lambda: test_vllm_params(client)),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n--- {name} ---")
        try:
            result = test_func()
            results.append((name, "✓ PASS", None))
        except Exception as e:
            results.append((name, "✗ FAIL", str(e)))
            print(f"Error: {e}")
    
    # Summary
    print("\n=== Test Summary ===")
    for name, status, error in results:
        print(f"{status}: {name}")
        if error:
            print(f"  Error: {error}")
    
    passed = sum(1 for _, status, _ in results if "PASS" in status)
    print(f"\nTotal: {passed}/{len(results)} passed")


if __name__ == "__main__":
    main()
