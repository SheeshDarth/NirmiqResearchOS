$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python scripts/eval_retrieval.py --dataset data/processed/eval/qa_labels.jsonl --k 3 5 8 --modes hybrid bm25 vector --full-query
