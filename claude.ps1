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

# Launch Claude Code
& "C:\Users\Momo\AppData\Roaming\Claude\claude-code\2.1.5\claude.exe"
