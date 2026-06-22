Add-Type -AssemblyName System.IO.Compression.FileSystem
$zipPath = "c:\Users\Admin\Desktop\anti\SMILE_Compiler_Week1.docx"
try {
    $zip = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
    $entry = $zip.GetEntry("word/document.xml")
    $stream = $entry.Open()
    $reader = New-Object System.IO.StreamReader($stream)
    $xmlString = $reader.ReadToEnd()
    $reader.Close()
    $zip.Dispose()
    
    [xml]$xml = $xmlString
    $ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
    $ns.AddNamespace("w", "http://schemas.openxmlformats.org/wordprocessingml/2006/main")
    
    $paragraphs = $xml.SelectNodes("//w:p", $ns)
    $content = @()
    foreach ($p in $paragraphs) {
        $texts = $p.SelectNodes(".//w:t", $ns)
        $pText = ""
        foreach ($t in $texts) {
            $pText += $t.InnerText
        }
        if ($pText) {
            $content += $pText
        }
    }
    $content | Out-File -FilePath "doc_content.txt" -Encoding UTF8
} catch {
    Write-Error $_
}
