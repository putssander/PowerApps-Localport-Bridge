# ================== Pronunciation_Bridge.ps1 ==================
# Role:  PAD bridge for pronunciation assessment
#        Power Apps → PAC → PAD → FastAPI (port 8000) → Phoneme Service
# Inputs (from PAD):
#   FileName    : base name with no extension
#   FolderName  : target folder for .wav and outputs
#   Base64Audio : audio in base64 (header already stripped in Power Apps)
#   ExpectedText: text the student was supposed to read (optional for transcribe-only)
#   Mode        : "transcribe" (default) or "assess" for full pronunciation assessment
# Output (to PAD):
#   JSON string with transcription and optional phoneme_assessment
# ================================================================

$ErrorActionPreference = 'Stop'

# ---------- 1. Read variables from PAD --------------------------------

$FileName     = '%FileName%'
$FolderName   = '%FolderName%'
$Base64Audio  = '%Base64Audio%'
$ExpectedText = '%ExpectedText%'
$Mode         = '%Mode%'

# ---------- 1a. Debug logging -----------------------------------------

$debugPath = "C:\Users\Admin\AppData\Local\Temp\Pronunciation_Temp\pad_debug.txt"
$tempFolder = "C:\Users\Admin\AppData\Local\Temp\Pronunciation_Temp"

if (-not (Test-Path -LiteralPath $tempFolder)) {
    New-Item -ItemType Directory -Path $tempFolder -Force | Out-Null
}

Add-Content $debugPath ("`n---- " + (Get-Date) +
    " | FileName='" + $FileName + 
    "' Mode='" + $Mode +
    "' ExpectedText='" + $ExpectedText.Substring(0, [Math]::Min(50, $ExpectedText.Length)) + "...' " +
    "' Base64Length=" + ($Base64Audio.Length))

# ---------- 2. Basic validation + defaults ----------------------------

if ([string]::IsNullOrWhiteSpace($Base64Audio)) {
    Write-Output '{"error": "No Base64Audio provided"}'
    exit 1
}

if ([string]::IsNullOrWhiteSpace($FileName)) {
    $FileName = "audio_" + (Get-Date -Format "yyyyMMdd_HHmmss")
}

if ([string]::IsNullOrWhiteSpace($FolderName)) {
    $FolderName = $tempFolder
}

if ([string]::IsNullOrWhiteSpace($Mode)) {
    $Mode = "transcribe"
}

if (-not (Test-Path -LiteralPath $FolderName)) {
    New-Item -ItemType Directory -Path $FolderName -Force | Out-Null
}

# Clean base64 string
$clean = $Base64Audio.Trim()

# ---------- 3. Call appropriate API endpoint --------------------------

$fastApiBaseUrl = "http://127.0.0.1:8000"

if ($Mode -eq "assess") {
    # Full pronunciation assessment
    if ([string]::IsNullOrWhiteSpace($ExpectedText)) {
        Write-Output '{"error": "ExpectedText required for assessment mode"}'
        exit 1
    }
    
    $endpoint = "$fastApiBaseUrl/assess"
    
    $bodyJson = @{
        file_name     = $FileName
        base64_audio  = $clean
        expected_text = $ExpectedText
    } | ConvertTo-Json -Depth 3
    
    Add-Content $debugPath ("Calling assess endpoint: " + $endpoint)
}
else {
    # Basic transcription (backward compatible)
    $endpoint = "$fastApiBaseUrl/transcribe"
    
    $bodyJson = @{
        file_name    = $FileName
        format       = "txt"
        base64_audio = $clean
    } | ConvertTo-Json -Depth 3
    
    Add-Content $debugPath ("Calling transcribe endpoint: " + $endpoint)
}

# ---------- 4. Make HTTP request --------------------------------------

try {
    $response = Invoke-RestMethod `
        -Uri $endpoint `
        -Method Post `
        -ContentType "application/json" `
        -Body $bodyJson `
        -TimeoutSec 300
}
catch {
    $errorMsg = @{
        error = "API call failed"
        details = $_.Exception.Message
    } | ConvertTo-Json
    
    Add-Content $debugPath ("ERROR: " + $_.Exception.Message)
    Write-Output $errorMsg
    exit 1
}

# ---------- 5. Process response ---------------------------------------

Add-Content $debugPath ("Response received: " + ($response | ConvertTo-Json -Depth 5).Substring(0, [Math]::Min(500, ($response | ConvertTo-Json).Length)))

if ($Mode -eq "assess") {
    # Return full assessment result
    $result = @{
        file_name           = $response.file_name
        transcription       = $response.transcription
        overall_score       = $response.phoneme_assessment.overall_score
        vowel_score         = $response.phoneme_assessment.vowel_score
        vowel_errors_count  = $response.phoneme_assessment.vowel_errors.Count
        focus_areas         = $response.phoneme_assessment.focus_areas -join "; "
        correct_vowels      = $response.phoneme_assessment.correct_vowels
        total_vowels        = $response.phoneme_assessment.total_vowels
        processing_time_ms  = $response.processing_time_ms
    }
    
    # Format score as percentage for easy display in PowerApps
    $result.overall_score_pct = [math]::Round($result.overall_score * 100, 1).ToString() + "%"
    $result.vowel_score_pct = [math]::Round($result.vowel_score * 100, 1).ToString() + "%"
    
    Write-Output ($result | ConvertTo-Json -Depth 3)
}
else {
    # Backward-compatible: just return transcription
    # Format matches original Whisper_Bridge.ps1 output
    Write-Output $response.transcription
}

Add-Content $debugPath ("---- Completed " + (Get-Date) + " ----")
