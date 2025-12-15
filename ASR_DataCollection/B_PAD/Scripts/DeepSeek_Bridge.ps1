$ErrorActionPreference = 'Stop'

# Use PAD input variable (or keep your default value)
$prompt = '%promptText%'   # or replace with 'hello from PAD'

# Build JSON safely and call local Ollama
$body = @{ model='deepseek-r1:8b'; prompt=$prompt; stream=$false } | ConvertTo-Json -Compress
$res  = Invoke-RestMethod -Uri 'http://127.0.0.1:11435/api/generate' -Method Post -ContentType 'application/json' -Body $body

# Extract only the assistant text and strip the <think> block
$text = $res.response
if ($null -ne $text) {
    $text = $text -replace '(?s)<think>.*?</think>\s*',''
    $text
} else {
    # Fallback: return raw JSON if 'response' missing
    $res | ConvertTo-Json -Compress
}
