<#
.SYNOPSIS
  Convert a .docx to PDF using Microsoft Word's rendering engine (COM automation).
.DESCRIPTION
  Opens the .docx in Word, exports as PDF, and closes. This gives the most
  accurate preview of what a Word user will see (fonts, math rendering, etc.).
  Requires Microsoft Word to be installed.
.PARAMETER docx
  Path to the input .docx file.
.PARAMETER pdf
  Path for the output .pdf file.
#>
$ErrorActionPreference = 'Stop'
if ($args.Count -lt 2) { Write-Error "Usage: docx-to-pdf.ps1 <input.docx> <output.pdf>"; exit 1 }
$docx = $args[0]
$pdf = $args[1]
if (-not (Test-Path $docx)) { Write-Error "File not found: $docx"; exit 1 }

# Kill any zombie Word processes first
Get-Process WINWORD -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Milliseconds 500

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {
  $doc = $word.Documents.Open($docx, $false, $true)
  $doc.ExportAsFixedFormat($pdf, 17)  # 17 = wdExportFormatPDF
  $doc.Close($false)
  Write-Output "PDF-OK: $pdf"
} catch {
  Write-Error "Word COM error: $($_.Exception.Message)"
} finally {
  $word.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
