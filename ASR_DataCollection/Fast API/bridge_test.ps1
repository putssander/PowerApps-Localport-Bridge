# 1) Pick any small WAV file that Whisper can handle
$wavPath = 'C:\Users\Admin\OneDrive - 城西国際大学\research\Artificial_ Intelligence\B_ASR_dev_big\1_Project Start_2025\GitHub_repo\PowerApps-Localport-Bridge\ASR_DataCollection\Fast API\test_audio.wav'

# quick sanity check
Write-Host "Test-Path:" (Test-Path $wavPath)

$bytes  = [System.IO.File]::ReadAllBytes($wavPath)
$base64 = [System.Convert]::ToBase64String($bytes)


# 3) Build JSON body for FastAPI
$body = @{
  file_name    = "Test_FastAPI_Standalone_0001"
  format       = "formattedDu"
  base64_audio = $base64
} | ConvertTo-Json

# 4) Call FastAPI directly
Invoke-RestMethod `
  -Uri "http://127.0.0.1:8000/transcribe" `
  -Method Post `
  -ContentType "application/json" `
  -Body $body
