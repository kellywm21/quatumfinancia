param(
    [string]$AppName = "app-damp-sun-5680",
    [string]$Token = $env:FLY_API_TOKEN
)

if (-not $Token) {
    Write-Error "Set FLY_API_TOKEN in your environment or pass --Token <token>"
    exit 1
}

if (-not (Get-Command flyctl -ErrorAction SilentlyContinue)) {
    Write-Error "flyctl is not installed or not on PATH. Install it first."
    exit 1
}

Write-Host "Authenticating with Fly..."
flyctl auth login --access-token $Token

Write-Host "Deploying app $AppName..."
flyctl deploy -a $AppName
