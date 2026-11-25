param([string]$ListFile, [string]$OutDir, [int]$Width = 850)
# Renders every page of every PDF named in $ListFile (one path per line) to
# PNG with Windows' own PDF renderer (Windows.Data.Pdf - nothing to install):
# <OutDir>\<pdf name without .pdf>-p<N>.png, $Width px wide (850 = the
# template canvas, so Word and Chromium pages land on the same pixel grid).
# Used by tools/word_audit.py.
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType = WindowsRuntime]
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$asTaskG = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })[0]
$asTaskA = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction' })[0]
function Await($op, [Type]$t) { $task = $asTaskG.MakeGenericMethod($t).Invoke($null, @($op)); $task.Wait(); $task.Result }
function AwaitA($op) { $task = $asTaskA.Invoke($null, @($op)); $task.Wait() }
foreach ($path in Get-Content $ListFile) {
  if (-not $path) { continue }
  $base = [IO.Path]::GetFileName($path) -replace '\.pdf$', ''
  $file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($path)) ([Windows.Storage.StorageFile])
  $pdf = Await ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
  for ($i = 0; $i -lt $pdf.PageCount; $i++) {
    $pg = $pdf.GetPage($i)
    $opt = New-Object Windows.Data.Pdf.PdfPageRenderOptions
    $opt.DestinationWidth = [uint32]$Width
    $ms = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
    AwaitA ($pg.RenderToStreamAsync($ms, $opt))
    $png = Join-Path $OutDir ("{0}-p{1}.png" -f $base, ($i + 1))
    $st = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($ms.GetInputStreamAt(0))
    $fs = [IO.File]::Create($png); $st.CopyTo($fs); $fs.Close(); $st.Dispose(); $ms.Dispose(); $pg.Dispose()
  }
}
