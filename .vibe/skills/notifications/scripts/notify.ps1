
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("success", "error", "input")]
    [string]$Event,

    [Parameter(Mandatory = $true)]
    [string]$Message
)

# ntfy configuration
$Topic = "ai1_vibe_status_updates"
$Server = "https://ntfy.sh"

# Notification settings
switch ($Event) {
    "success" {
        $Title = "Klar"
        $Tags = "white_check_mark"
        $Priority = "default"
    }

    "error" {
        $Title = "Fel"
        $Tags = "warning"
        $Priority = "high"
    }

    "input" {
        $Title = "Fråga"
        $Tags = "raising_hand"
        $Priority = "high"
    }
}

# Send notification
try {
    $Headers = @{
        "Title"    = $Title
        "Tags"     = $Tags
        "Priority" = $Priority
    }

    Invoke-RestMethod `
        -Uri "$Server/$Topic" `
        -Method Post `
        -Headers $Headers `
        -ContentType "text/plain; charset=utf-8" `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($Message)) `
        -TimeoutSec 10 `
        -ErrorAction Stop | Out-Null

    Write-Host "Notification sent: $Event"
    exit 0
}
catch {
    Write-Error "Failed to send notification: $_"
    exit 1
}
