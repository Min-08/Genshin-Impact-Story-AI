Set-Location $PSScriptRoot
if (Get-Command py -ErrorAction SilentlyContinue) {
  py -3 build_amber_db.py
} else {
  python build_amber_db.py
}
