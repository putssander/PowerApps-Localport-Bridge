# ============================================PowershellScriptVer5.1===========
# TranscriptionPAD_ver3 – Whisper bridge script (Port 9000 explicit)
# Inputs (from PAD):
#   %FileName%    - base name (no extension), e.g. recorded_test_20251113_093000_ABC123
#   %FolderName%  - target folder path, e.g. C:\Users\Admin\AppData\Local\Temp\Whisper_Temp
#   %Base64Audio% - audio in base64 (headerless or headered)
# Output (to PAD):
#   TranscriptionText - plain text transcript written to stdout
# ============================================

$ErrorActionPreference = 'Stop'

# --------------------------------------------
# SECTION 1: Read PAD variables
# --------------------------------------------
$FileName    = '%FileName%'
$FolderName  = 'C:\WhisperData'
$Base64Audio = '%Base64Audio%'

# --------------------------------------------
# SECTION 2: Basic validation and fallbacks
# --------------------------------------------

if ([string]::IsNullOrWhiteSpace($Base64Audio)) {
    Write-Output "ERROR: No Base64Audio provided."
    exit 1
}

if ([string]::IsNullOrWhiteSpace($FileName)) {
    $FileName = "audio_" + (Get-Date -Format "yyyyMMdd_HHmmss")
}

if ([string]::IsNullOrWhiteSpace($FolderName)) {
    $FolderName = "C:\Users\Admin\AppData\Local\Temp\Whisper_Temp"
}

if (-not (Test-Path -LiteralPath $FolderName)) {
    New-Item -ItemType Directory -Path $FolderName -Force | Out-Null
}

$wavPath = Join-Path $FolderName ($FileName + ".wav")
$txtPath = Join-Path $FolderName ($FileName + ".txt")

# --------------------------------------------
# SECTION 3: Decode Base64 → WAV
# --------------------------------------------

# Power Apps already removed the data:audio/...;base64, header
# so we just normalize whitespace (if any) and decode.
$clean = ($Base64Audio -replace '\s','')

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

# --------------------------------------------
# SECTION 4: Whisper call via webservice on port 9000 (PS 5.1, no HttpClient)
# --------------------------------------------

# CHANGE THIS PORT if your container is bound to a different host port (e.g. 9001).
$WhisperURL = "http://127.0.0.1:9001/asr?encode=true&task=transcribe&language=en&output=srt"

# Build multipart/form-data body manually (PowerShell 5.1-safe)
$boundary = "------------------------" + ([System.Guid]::NewGuid().ToString("N"))
$LF = "`r`n"

try {
    if (-not (Test-Path -LiteralPath $wavPath)) {
        Write-Output ("ERROR: WAV file not found at path: " + $wavPath)
        exit 1
    }

    $fileNameOnly = [System.IO.Path]::GetFileName($wavPath)

    # Multipart header for the audio_file field
    $header =
        "--$boundary$LF" +
        "Content-Disposition: form-data; name=`"audio_file`"; filename=`"$fileNameOnly`"$LF" +
        "Content-Type: audio/wav$LF$LF"

    # Closing boundary
    $footer = "$LF--$boundary--$LF"

    # Convert header/footer to bytes, read WAV bytes
    $headerBytes = [System.Text.Encoding]::ASCII.GetBytes($header)
    $fileBytes   = [System.IO.File]::ReadAllBytes($wavPath)
    $footerBytes = [System.Text.Encoding]::ASCII.GetBytes($footer)

    # Allocate one combined byte[] for the full multipart body
    $bodyBytes = New-Object byte[] ($headerBytes.Length + $fileBytes.Length + $footerBytes.Length)
    [Array]::Copy($headerBytes, 0, $bodyBytes, 0, $headerBytes.Length)
    [Array]::Copy($fileBytes,   0, $bodyBytes, $headerBytes.Length, $fileBytes.Length)
    [Array]::Copy($footerBytes, 0, $bodyBytes, $headerBytes.Length + $fileBytes.Length, $footerBytes.Length)

    # Send POST with raw multipart body
    $contentType = "multipart/form-data; boundary=$boundary"

    $res = Invoke-RestMethod `
        -Uri $WhisperURL `
        -Method Post `
        -ContentType $contentType `
        -Body $bodyBytes
}
catch {
    Write-Output ("ERROR: Whisper HTTP call failed on port 9000 : " + $_.Exception.Message)
    exit 1
}

# --------------------------------------------
# SECTION 5: Extract transcript
# --------------------------------------------

$transcript = $null

if ($res -is [string]) {
    # Whisper returned plain text or SRT
    $transcript = $res
}
elseif ($res.PSObject.Properties.Name -contains 'text') {
    # Whisper returned JSON with a 'text' property
    $transcript = $res.text
}
else {
    # Fallback: return raw JSON so you can see the structure
    $transcript = ($res | ConvertTo-Json -Compress)
}

if ([string]::IsNullOrWhiteSpace($transcript)) {
    $transcript = "ERROR: Whisper returned empty text."
}

# --------------------------------------------
# SECTION 6: Save transcript (.txt)
# --------------------------------------------

try {
    [System.IO.File]::WriteAllText($txtPath, $transcript, [System.Text.Encoding]::UTF8)
}
catch {
    $transcript += "`n[Warning: Could not write transcript file: $($_.Exception.Message)]"
}

# --------------------------------------------
# SECTION 7: Return transcript to PAD
# --------------------------------------------

Write-Output $transcript
