# Close the running game so a new build can be installed. It never saves: Maxim's own saves are
# left exactly as he made them, and progress since his last save is not kept.
# Usage: powershell -File D:\Dev\Games\jk-rpg\tools\close_game.ps1
$proc = Get-Process openjkdf2-64 -ErrorAction SilentlyContinue
if (-not $proc) { 'Game not running.'; exit 0 }
$proc.CloseMainWindow() | Out-Null
if (-not $proc.WaitForExit(10000)) { $proc.Kill(); $proc.WaitForExit() }
'Closed the game without saving.'
exit 0
