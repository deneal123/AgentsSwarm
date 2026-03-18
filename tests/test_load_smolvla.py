from transformers import AutoModel
try:
    model = AutoModel.from_pretrained('lerobot/smolvla_base', trust_remote_code=True, torch_dtype='auto')
    print(f'Loaded: {type(model)}')
    print(f'Params: {sum(p.numel() for p in model.parameters()):,}')
except Exception as e:
    print(f'Error: {e}')