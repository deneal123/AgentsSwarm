uv run vllm-service serve \
  --model Qwen/Qwen2.5-7B-Instruct \
  --data-parallel-size 1 \
  --data-parallel-rank 0 \
  --host 0.0.0.0 \
  --port 8005 \
  --log-level INFO

curl -v http://localhost:8005/health
curl -v http://localhost:8005/ready
curl -v http://localhost:8005/v1/models

curl -s -X POST http://localhost:8005/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"Qwen/Qwen2.5-7B-Instruct",
    "messages":[{"role":"user","content":"Привет, как дела?"}],
    "temperature":0.7
  }'