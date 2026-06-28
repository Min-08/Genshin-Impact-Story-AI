$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
python scripts/lore_chat.py @args
exit $LASTEXITCODE
