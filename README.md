# nvidia_isaac_simulation


## install dependencies
uv sync \
  --index-strategy unsafe-best-match \
  --prerelease=allow \
  --extra dev

## add dependencies to the project
uv add \
  --index-strategy unsafe-best-match \
  --prerelease=allow \
  lark

## lock dependencies
uv lock \
  --index-strategy unsafe-best-match \
  --prerelease=allow \
  
## run example
uv run \
  --index-strategy unsafe-best-match \
  --prerelease=allow \
  example.py

## tests
uv run \ 
  --index-strategy unsafe-best-match \
  --prerelease=allow \
  python -m pytest


### TODO:

- [] Починить гравитацию в сцене (возможно, проблема с единицами измерения или настройками физики)