# Launch Claude Code with full permissions
# Permissions configured in: C:\Users\Momo\.claude\settings.json

$settingsPath = "$env:USERPROFILE\.claude\settings.json"
$settings = @{
    permissions = @{
        allow = @(
            "Bash"
            "Read"
            "Write"
            "Edit"
            "MultiEdit"
            "Glob"
            "Grep"
            "LS"
            "Task"
            "WebFetch"
            "WebSearch"
            "NotebookEdit"
            "TodoRead"
            "TodoWrite"
        )
        defaultMode = "dontAsk"
    }
    sandbox = @{
        enabled = $false
    }
    autoUpdatesChannel = "latest"
}

# Create .claude directory if it doesn't exist
$claudeDir = Split-Path $settingsPath
if (-not (Test-Path $claudeDir)) {
    New-Item -ItemType Directory -Path $claudeDir -Force | Out-Null
}

# Write settings
$settings | ConvertTo-Json -Depth 4 | Set-Content $settingsPath -Encoding UTF8

# Launch Claude Code (find latest version automatically)
$claudeExe = Get-ChildItem "$env:APPDATA\Claude\claude-code\*\claude.exe" -ErrorAction SilentlyContinue |
    Sort-Object { [version]$_.Directory.Name } -Descending |
    Select-Object -First 1

if ($claudeExe) {
    & $claudeExe.FullName
} else {
    Write-Error "Claude Code not found in $env:APPDATA\Claude\claude-code"
    pause
}
