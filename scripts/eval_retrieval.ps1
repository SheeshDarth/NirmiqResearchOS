$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..")
python scripts/eval_retrieval.py --dataset data/processed/eval/demo_academic_qa.jsonl --k 3 5 8 --modes hybrid bm25 --output data/processed/eval/demo_retrieval_metrics.json
