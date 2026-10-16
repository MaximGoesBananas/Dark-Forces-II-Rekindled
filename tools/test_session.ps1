# Windows entry point for the background test session (see DEVELOPING.md, "Testing without taking
# Maxim's screen"). Keeps the WSL side awake while a session runs, then forwards to test_session.sh.
#   powershell -File tools\test_session.ps1 start -autostart -sp -episode JK1 -map 01narshadda.jkl
#   powershell -File tools\test_session.ps1 key shift+Escape | type "givexp 100" | click X Y | fire MS | shot NAME
#   powershell -File tools\test_session.ps1 stop      (also stops the virtual screen and the keep-alive)
$script = '/mnt/d/Dev/Games/jk-rpg/tools/test_session.sh'
$keepAliveTag = 'jkrpg-keepalive'
$keepAlive = Get-CimInstance Win32_Process -Filter "Name='wsl.exe'" | Where-Object { $_.CommandLine -match $keepAliveTag }

if ($args.Count -gt 0 -and $args[0] -eq 'start' -and -not $keepAlive) {
    # WSL shuts Linux down when no command is attached; this hidden sleep keeps the test game alive.
    # One quoted argument string: Start-Process does not quote list elements that contain spaces.
    Start-Process wsl.exe -ArgumentList "-d Ubuntu-24.04 -- bash -c `"exec -a $keepAliveTag sleep 7200`"" -WindowStyle Hidden | Out-Null
}

wsl -d Ubuntu-24.04 -- bash $script @args
$code = $LASTEXITCODE

if ($args.Count -gt 0 -and $args[0] -eq 'stop') {
    $keepAlive | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
}
exit $code
