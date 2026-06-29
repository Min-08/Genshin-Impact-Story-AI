$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
python scripts/lore_chat.py --auto-start-llm @args
exit $LASTEXITCODE
