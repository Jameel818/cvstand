param([string]$ListFile, [string]$OutDir, [string]$Csv)
# Converts every .docx named in $ListFile (one path per line) to PDF with REAL
# Microsoft Word: <OutDir>\<name>.word.pdf, and appends "name,pages,w,h" rows
# to $Csv. Used by tools/word_audit.py.
#
# Safety (the user keeps their own Word documents open - never touch them):
# - Word is started here and only the WINWORD process that appeared after the
#   start is treated as ours; an instance that already holds documents is
#   refused (New-Object may attach to a running Word).
# - Only our own PID is ever stopped. Never Quit/taskkill any other Word.
# Must run INSIDE Start-Job: a direct child powershell stalls Word COM on this PC
# (tools/word_audit.py launches it that way).
$before = @(Get-Process WINWORD -ErrorAction SilentlyContinue | ForEach-Object { $_.Id })
$w = New-Object -ComObject Word.Application
Start-Sleep -Milliseconds 700
$mine = @(Get-Process WINWORD -ErrorAction SilentlyContinue | Where-Object { $before -notcontains $_.Id } | ForEach-Object { $_.Id })
($mine -join ";") | Out-File -Encoding ascii ($Csv + ".pid")
if ($mine.Count -eq 0 -or $w.Documents.Count -gt 0) { "REFUSED" | Out-File -Encoding ascii -Append $Csv; return }
$w.Visible = $false; $w.DisplayAlerts = 0
try {
  foreach ($path in Get-Content $ListFile) {
    if (-not $path) { continue }
    # full, normalised paths: with the raw Join-Path string the PDF export
    # hung on every file (even a blank one) until the job timed out (2026-11-24)
    $path = [IO.Path]::GetFullPath($path)
    $name = [IO.Path]::GetFileNameWithoutExtension($path)
    $pdf = [IO.Path]::GetFullPath((Join-Path $OutDir ($name + ".word.pdf")))
    try {
      $d = $w.Documents.Open($path, $false, $true, $false)
      $pages = $d.ComputeStatistics(2)
      $d.ExportAsFixedFormat($pdf, 17)
      $ps = $d.Sections(1).PageSetup
      ("{0},{1},{2},{3}" -f $name, $pages, $ps.PageWidth, $ps.PageHeight) | Out-File -Encoding utf8 -Append $Csv
      $d.Close(0)
    } catch {
      ("{0},ERR,0,0" -f $name) | Out-File -Encoding utf8 -Append $Csv; ("ERR " + $_.Exception.Message) | Out-File -Encoding utf8 -Append ($Csv + ".log")
    }
  }
} finally {
  try { $w.Quit(0) } catch {}
  Start-Sleep -Seconds 2
  foreach ($id in $mine) { Stop-Process -Id $id -Force -ErrorAction SilentlyContinue }
}
