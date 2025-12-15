# ================== TranscriptionPAD_FastAPI_v1.ps1 ==================
# Role:  PAD bridge
#        Power Apps → PAC → PAD → FastAPI (port 8000) → Whisper (port 9000/9001)
# Inputs (from PAD):
#   FileName    : base name with no extension
#   FolderName  : target folder for .wav and .txt
#   Base64Audio : audio in base64 (header already stripped in Power Apps)
# Output (to PAD):
#   Transcription : plain text transcription written to stdout
# =====================================================================

Add-Content $debugPath ("`n---- " + (Get-Date) +
    " | FileName='%FileName%' FolderName='%FolderName%' Base64Length=" +
    ($Base64Audio.Length))


$ErrorActionPreference = 'Stop'

# 1) Read variables from PAD
$FileName    = '%FileName%'
$FolderName  = '%FolderName%'
$Base64Audio = '%Base64Audio%'


# 1a) Debug log path
$debugPath = "C:\Users\Admin\AppData\Local\Temp\Whisper_Temp\pad_debug.txt"

Add-Content $debugPath ("`n---- " + (Get-Date) +
    " | FileName='" + $FileName + "' FolderName='" + $FolderName +
    "' Base64Length=" + ($Base64Audio.Length))

# ---------- 2. Basic validation + defaults ----------------------------

if ([string]::IsNullOrWhiteSpace($Base64Audio)) {
    Write-Output "ERROR: No Base64Audio provided."
    exit 1
}

if ([string]::IsNullOrWhiteSpace($FileName)) {
    $FileName = "audio_" + (Get-Date -Format "yyyyMMdd_HHmmss")
}

if ([string]::IsNullOrWhiteSpace($FolderName)) {
    # Always override folder to Whisper temp folder (ignore PAC)
$FolderName = "C:\Users\Admin\AppData\Local\Temp\Whisper_Temp"

}

if (-not (Test-Path -LiteralPath $FolderName)) {
    New-Item -ItemType Directory -Path $FolderName -Force | Out-Null
}

$wavPath = Join-Path $FolderName ($FileName + ".wav")
$txtPath = Join-Path $FolderName ($FileName + ".txt")

# ---------- 3. Decode base64 → WAV file -------------------------------

# Clean any whitespace and any accidental header (just in case).
$clean = $Base64Audio
$clean = $Base64Audio.Trim()


try {
    $bytes = [System.Convert]::FromBase64String($clean)
}
catch {
    Write-Output ("ERROR: Base64 decode failed: " + $_.Exception.Message)
    exit 1
}

try {
    [System.IO.File]::WriteAllBytes($wavPath, $bytes)
}
catch {
    Write-Output ("ERROR: Failed to write WAV file: " + $_.Exception.Message)
    exit 1
}

# ---------- 4. Call FastAPI bridge on port 8000 -----------------------

# This URL must match your FastAPI app:
#   uvicorn whisper_api:app --host 0.0.0.0 --port 8000
$fastApiUrl = "http://127.0.0.1:8000/transcribe"

# Build JSON body for FastAPI
$bodyJson = @{
    file_name    = $FileName          # same base name you used above
    format       = "formattedDu"
    base64_audio = $clean             # cleaned base64 string
} | ConvertTo-Json -Depth 3

try {
    $response = Invoke-RestMethod `
        -Uri $fastApiUrl `
        -Method Post `
        -ContentType "application/json" `
        -Body $bodyJson
}
catch {
    Write-Output ("ERROR: FastAPI HTTP call failed: " + $_.Exception.Message)
    exit 1
}

if ($null -eq $response) {
    Write-Output "ERROR: FastAPI returned no data."
    exit 1
}

# ---------- 5. Extract transcription text -----------------------------

# FastAPI returns:
#   { "file_name": "...", "transcription": "..." }
$Transcription = $null

if ($response.PSObject.Properties.Name -contains 'transcription') {
    $Transcription = $response.transcription
}
elseif ($response.PSObject.Properties.Name -contains 'text') {
    $Transcription = $response.text
}
else {
    # Fallback: show raw JSON so you can see the shape
    $Transcription = ($response | ConvertTo-Json -Compress)
}

if ([string]::IsNullOrWhiteSpace($Transcription)) {
    $Transcription = "ERROR: FastAPI response did not contain transcription text."
}

# ---------- 6. Save transcript to .txt (same base name) ---------------

try {
    [System.IO.File]::WriteAllText($txtPath, $Transcription, [System.Text.Encoding]::UTF8)
}
catch {
    # Keep going, but append a warning into the text that goes back to PAC.
    $Transcription += "`n[Warning: Could not write transcript file: $($_.Exception.Message)]"
}

# ---------- 7. Return transcription to PAC / Power Apps ---------------

Write-Output $Transcription
