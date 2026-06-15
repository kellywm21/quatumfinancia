param(
    [string]$BaseUrl = 'http://127.0.0.1:8000'
)

function Fail([string]$msg){
    Write-Error $msg
    exit 1
}

Write-Output "Starting verification against $BaseUrl"

$unique = ([guid]::NewGuid().ToString()).Substring(0,8)
$username = "demo$unique"
$email = "demo+$unique@advancia.com"

try{
    Write-Output "Registering user $username..."
    $regBody = @{ email = $email; username = $username; password = 'demopassword123'; full_name = 'Demo User' }
    $reg = Invoke-RestMethod -Uri "$BaseUrl/auth/register" -Method POST -ContentType 'application/json' -Body ($regBody | ConvertTo-Json -Depth 5) -TimeoutSec 20
    Write-Output "Registered: $($reg.email)"
} catch {
    $msg = $_.Exception.Response | ForEach-Object { try { $_ | ConvertTo-Json -Depth 5 } catch { $_.ToString() } }
    Write-Output "Register failed or already exists, continuing: $msg"
}

try{
    Write-Output "Logging in..."
    $login = Invoke-RestMethod -Uri "$BaseUrl/auth/login" -Method POST -Body @{ username = $username; password = 'demopassword123' } -TimeoutSec 20
    $token = $login.access_token
    if (-not $token){ Fail 'Login did not return access token' }
    $headers = @{ Authorization = "Bearer $token" }
    Write-Output "Login successful"
} catch {
    Fail "Login failed: $($_.Exception.Message)"
}

try{
    Write-Output "Creating cardholder..."
    # Use the demo user's email in test mode so the demo user can issue cards for this cardholder
    $chBody = @{ email = $email; business_name = 'Advancia Demo' }
    $cardholder = Invoke-RestMethod -Uri "$BaseUrl/api/cardholders/" -Method POST -Headers $headers -ContentType 'application/json' -Body ($chBody | ConvertTo-Json -Depth 5) -TimeoutSec 20
    Write-Output "Cardholder created: $($cardholder.account_token)"
} catch {
    Fail "Cardholder creation failed: $($_.Exception.Message)"
}

try{
    Write-Output "Issuing virtual card..."
    $cardBody = @{ account_token = $cardholder.account_token; card_type = 'VIRTUAL'; spend_limit = 15000000; spend_limit_duration = 'MONTHLY'; memo = 'Demo card' }
    $card = Invoke-RestMethod -Uri "$BaseUrl/api/cards/" -Method POST -Headers $headers -ContentType 'application/json' -Body ($cardBody | ConvertTo-Json -Depth 5) -TimeoutSec 20
    Write-Output "Card issued: $($card.card_token) -> financial_account_token: $($card.financial_account_token)"
} catch {
    Fail "Card issuance failed: $($_.Exception.Message)"
}

try{
    Write-Output "Checking financial account balance..."
    $balance = Invoke-RestMethod -Uri "$BaseUrl/api/financial-accounts/$($card.financial_account_token)" -Method GET -Headers $headers -TimeoutSec 20
    Write-Output "Balance: Available=$($balance.available_balance) Pending=$($balance.pending_balance)"
} catch {
    Fail "Balance check failed: $($_.Exception.Message)"
}

try{
    Write-Output "Creating sample payment..."
    $paymentBody = @{ amount = 1.23; currency = 'USD'; description = 'Demo payment' }
    $payment = Invoke-RestMethod -Uri "$BaseUrl/api/payments/" -Method POST -Headers $headers -ContentType 'application/json' -Body ($paymentBody | ConvertTo-Json -Depth 5) -TimeoutSec 20
    Write-Output "Payment created: $($payment.transaction_id) amount=$($payment.amount) status=$($payment.status)"
} catch {
    Fail "Payment creation failed: $($_.Exception.Message)"
}

Write-Output "Verification completed successfully"
exit 0
