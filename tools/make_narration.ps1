$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$segments = Get-Content -Raw -Encoding UTF8 (Join-Path $PSScriptRoot 'demo_segments.json') | ConvertFrom-Json
$voice = New-Object -ComObject SAPI.SpVoice
$voices = $voice.GetVoices()
foreach ($candidate in $voices) {
    if ($candidate.GetDescription() -like '*Huihui*') { $voice.Voice = $candidate; break }
}
$voice.Rate = 2
$voice.Volume = 100
$audioDir = Join-Path $taskRoot 'docs\demo_audio'
New-Item -ItemType Directory -Force -Path $audioDir | Out-Null
foreach ($segment in $segments) {
    $stream = New-Object -ComObject SAPI.SpFileStream
    $stream.Format.Type = 22
    $stream.Open((Join-Path $audioDir ($segment.key + '.wav')), 3, $false)
    $voice.AudioOutputStream = $stream
    [void]$voice.Speak($segment.text)
    $stream.Close()
}
Write-Output 'Chinese narration generated.'
