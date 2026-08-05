param(
  [Parameter(Mandatory = $true)]
  [string]$OutputPath,

  [string]$DocJsonPath,
  [string]$DocJsonBase64Utf8,
  [string]$Title,
  [string[]]$Paragraphs
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function ConvertTo-AbsolutePath {
  param([Parameter(Mandatory = $true)][string]$PathValue)

  if ([System.IO.Path]::IsPathRooted($PathValue)) {
    return [System.IO.Path]::GetFullPath($PathValue)
  }

  return [System.IO.Path]::GetFullPath((Join-Path (Get-Location) $PathValue))
}

function ConvertTo-StructuredObject {
  param([Parameter(Mandatory = $true)]$Value)

  if ($null -eq $Value) {
    return $null
  }

  if ($Value -is [System.Collections.IDictionary]) {
    $result = [pscustomobject]@{}
    foreach ($key in $Value.Keys) {
      $result | Add-Member -NotePropertyName ([string]$key) -NotePropertyValue (ConvertTo-StructuredObject -Value $Value[$key])
    }
    return $result
  }

  if (($Value -is [System.Collections.IEnumerable]) -and -not ($Value -is [string])) {
    $items = @()
    foreach ($item in $Value) {
      $items += ,(ConvertTo-StructuredObject -Value $item)
    }
    return $items
  }

  return $Value
}

function Parse-JsonDocument {
  param([Parameter(Mandatory = $true)][string]$JsonText)

  Add-Type -AssemblyName System.Web.Extensions
  $serializer = New-Object System.Web.Script.Serialization.JavaScriptSerializer
  $serializer.MaxJsonLength = 67108864
  $serializer.RecursionLimit = 100
  return ConvertTo-StructuredObject -Value ($serializer.DeserializeObject($JsonText))
}

function Get-DocumentDefinition {
  param(
    [string]$JsonPath,
    [string]$JsonBase64Utf8,
    [string]$DocumentTitle,
    [string[]]$DocumentParagraphs
  )

  if ($JsonBase64Utf8) {
    $rawJson = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String($JsonBase64Utf8))
    $doc = Parse-JsonDocument -JsonText $rawJson
    if (-not $doc) {
      throw 'Document JSON decoded from base64 is empty.'
    }
    return $doc
  }

  if ($JsonPath) {
    $absoluteJsonPath = ConvertTo-AbsolutePath -PathValue $JsonPath
    if (-not (Test-Path -LiteralPath $absoluteJsonPath -PathType Leaf)) {
      throw "Document JSON not found: $absoluteJsonPath"
    }

    $rawJson = Get-Content -LiteralPath $absoluteJsonPath -Raw -Encoding UTF8
    $doc = Parse-JsonDocument -JsonText $rawJson
    if (-not $doc) {
      throw "Document JSON is empty: $absoluteJsonPath"
    }
    return $doc
  }

  if (-not $DocumentTitle -and (-not $DocumentParagraphs -or $DocumentParagraphs.Count -eq 0)) {
    throw 'Provide -DocJsonPath, -DocJsonBase64Utf8, or at least -Title / -Paragraphs.'
  }

  return [pscustomobject]@{
    title = $DocumentTitle
    paragraphs = $DocumentParagraphs
  }
}

function Escape-XmlText {
  param([string]$Text)

  if ($null -eq $Text) {
    return ''
  }

  return [System.Security.SecurityElement]::Escape([string]$Text)
}

function New-TextRunXml {
  param([Parameter(Mandatory = $true)][string]$Text)

  $escaped = Escape-XmlText -Text $Text
  $preserve = ''
  if ($Text.StartsWith(' ') -or $Text.EndsWith(' ') -or $Text.Contains('  ')) {
    $preserve = ' xml:space="preserve"'
  }
  return "<w:r><w:t$preserve>$escaped</w:t></w:r>"
}

function New-ParagraphXml {
  param(
    [string]$Text,
    [string]$StyleId
  )

  $paragraphProperties = ''
  if ($StyleId) {
    $paragraphProperties = "<w:pPr><w:pStyle w:val=""$StyleId""/></w:pPr>"
  }

  if ([string]::IsNullOrEmpty($Text)) {
    return "<w:p>$paragraphProperties</w:p>"
  }

  return "<w:p>$paragraphProperties$(New-TextRunXml -Text $Text)</w:p>"
}

function Get-DocumentXml {
  param([Parameter(Mandatory = $true)]$DocumentDefinition)

  $paragraphXml = New-Object System.Collections.Generic.List[string]

  if ($DocumentDefinition.PSObject.Properties.Name -contains 'title' -and -not [string]::IsNullOrWhiteSpace([string]$DocumentDefinition.title)) {
    [void]$paragraphXml.Add((New-ParagraphXml -Text ([string]$DocumentDefinition.title) -StyleId 'Title'))
  }

  if ($DocumentDefinition.PSObject.Properties.Name -contains 'subtitle' -and -not [string]::IsNullOrWhiteSpace([string]$DocumentDefinition.subtitle)) {
    [void]$paragraphXml.Add((New-ParagraphXml -Text ([string]$DocumentDefinition.subtitle) -StyleId 'Subtitle'))
  }

  if ($DocumentDefinition.PSObject.Properties.Name -contains 'paragraphs' -and $DocumentDefinition.paragraphs) {
    foreach ($paragraph in $DocumentDefinition.paragraphs) {
      [void]$paragraphXml.Add((New-ParagraphXml -Text ([string]$paragraph) -StyleId 'BodyText'))
    }
  }

  if ($DocumentDefinition.PSObject.Properties.Name -contains 'sections' -and $DocumentDefinition.sections) {
    foreach ($section in $DocumentDefinition.sections) {
      if ($section.PSObject.Properties.Name -contains 'heading' -and -not [string]::IsNullOrWhiteSpace([string]$section.heading)) {
        [void]$paragraphXml.Add((New-ParagraphXml -Text ([string]$section.heading) -StyleId 'Heading1'))
      }
      if ($section.PSObject.Properties.Name -contains 'paragraphs' -and $section.paragraphs) {
        foreach ($paragraph in $section.paragraphs) {
          [void]$paragraphXml.Add((New-ParagraphXml -Text ([string]$paragraph) -StyleId 'BodyText'))
        }
      }
    }
  }

  if ($paragraphXml.Count -eq 0) {
    [void]$paragraphXml.Add((New-ParagraphXml -Text '' -StyleId 'BodyText'))
  }

  $sectPr = @'
<w:sectPr>
  <w:pgSz w:w="11906" w:h="16838"/>
  <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>
</w:sectPr>
'@

  return @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <w:body>
    $($paragraphXml -join "`n    ")
    $sectPr
  </w:body>
</w:document>
"@
}

function Get-StylesXml {
  return @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:docDefaults>
    <w:rPrDefault>
      <w:rPr>
        <w:lang w:val="zh-CN" w:eastAsia="zh-CN" w:bidi="ar-SA"/>
      </w:rPr>
    </w:rPrDefault>
    <w:pPrDefault/>
  </w:docDefaults>
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
    <w:qFormat/>
    <w:rPr>
      <w:sz w:val="22"/>
      <w:szCs w:val="22"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="BodyText"/>
    <w:qFormat/>
    <w:pPr>
      <w:spacing w:before="0" w:after="240"/>
    </w:pPr>
    <w:rPr>
      <w:b/>
      <w:sz w:val="32"/>
      <w:szCs w:val="32"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Subtitle">
    <w:name w:val="Subtitle"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="BodyText"/>
    <w:qFormat/>
    <w:pPr>
      <w:spacing w:before="0" w:after="200"/>
    </w:pPr>
    <w:rPr>
      <w:i/>
      <w:color w:val="666666"/>
      <w:sz w:val="22"/>
      <w:szCs w:val="22"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="BodyText"/>
    <w:uiPriority w:val="9"/>
    <w:qFormat/>
    <w:pPr>
      <w:spacing w:before="240" w:after="120"/>
      <w:keepNext/>
    </w:pPr>
    <w:rPr>
      <w:b/>
      <w:sz w:val="28"/>
      <w:szCs w:val="28"/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="BodyText">
    <w:name w:val="Body Text"/>
    <w:basedOn w:val="Normal"/>
    <w:qFormat/>
    <w:pPr>
      <w:spacing w:after="120" w:line="360" w:lineRule="auto"/>
    </w:pPr>
    <w:rPr>
      <w:sz w:val="22"/>
      <w:szCs w:val="22"/>
    </w:rPr>
  </w:style>
</w:styles>
'@
}

function Get-SettingsXml {
  return @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:zoom w:percent="100"/>
  <w:defaultTabStop w:val="420"/>
  <w:characterSpacingControl w:val="doNotCompress"/>
  <w:compat/>
</w:settings>
'@
}

function Get-WebSettingsXml {
  return @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:webSettings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:optimizeForBrowser/>
  <w:allowPNG/>
</w:webSettings>
'@
}

function Get-AppXml {
  param([Parameter(Mandatory = $true)][string]$ApplicationName)

  return @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>$ApplicationName</Application>
</Properties>
"@
}

function Get-CoreXml {
  param([Parameter(Mandatory = $true)]$DocumentDefinition)

  $title = ''
  if ($DocumentDefinition.PSObject.Properties.Name -contains 'title') {
    $title = Escape-XmlText -Text ([string]$DocumentDefinition.title)
  }
  $now = [DateTime]::UtcNow.ToString('s') + 'Z'

  return @"
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>$title</dc:title>
  <dc:creator>WindClaw</dc:creator>
  <cp:lastModifiedBy>WindClaw</cp:lastModifiedBy>
  <dcterms:created xsi:type="dcterms:W3CDTF">$now</dcterms:created>
  <dcterms:modified xsi:type="dcterms:W3CDTF">$now</dcterms:modified>
</cp:coreProperties>
"@
}

function Get-ContentTypesXml {
  return @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>
  <Override PartName="/word/webSettings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.webSettings+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
'@
}

function Get-PackageRelsXml {
  return @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
'@
}

function Get-DocumentRelsXml {
  return @'
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings" Target="settings.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/webSettings" Target="webSettings.xml"/>
</Relationships>
'@
}

function Write-ZipTextEntry {
  param(
    [Parameter(Mandatory = $true)]$Archive,
    [Parameter(Mandatory = $true)][string]$EntryPath,
    [Parameter(Mandatory = $true)][string]$Content
  )

  $entry = $Archive.CreateEntry($EntryPath)
  $writer = New-Object System.IO.StreamWriter($entry.Open(), (New-Object System.Text.UTF8Encoding($false)))
  try {
    $writer.Write($Content)
  } finally {
    $writer.Dispose()
  }
}

function New-DocxFromDefinition {
  param(
    [Parameter(Mandatory = $true)]$DocumentDefinition,
    [Parameter(Mandatory = $true)][string]$TargetPath
  )

  Add-Type -AssemblyName System.IO.Compression
  Add-Type -AssemblyName System.IO.Compression.FileSystem

  $absoluteTargetPath = ConvertTo-AbsolutePath -PathValue $TargetPath
  $targetDir = Split-Path -Parent $absoluteTargetPath

  if (-not (Test-Path -LiteralPath $targetDir)) {
    New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
  }

  if (Test-Path -LiteralPath $absoluteTargetPath) {
    Remove-Item -LiteralPath $absoluteTargetPath -Force
  }

  $fileStream = [System.IO.File]::Open($absoluteTargetPath, [System.IO.FileMode]::CreateNew)
  try {
    $archive = New-Object System.IO.Compression.ZipArchive($fileStream, [System.IO.Compression.ZipArchiveMode]::Create, $false)
    try {
      Write-ZipTextEntry -Archive $archive -EntryPath '[Content_Types].xml' -Content (Get-ContentTypesXml)
      Write-ZipTextEntry -Archive $archive -EntryPath '_rels/.rels' -Content (Get-PackageRelsXml)
      Write-ZipTextEntry -Archive $archive -EntryPath 'docProps/core.xml' -Content (Get-CoreXml -DocumentDefinition $DocumentDefinition)
      Write-ZipTextEntry -Archive $archive -EntryPath 'docProps/app.xml' -Content (Get-AppXml -ApplicationName 'WindClaw')
      Write-ZipTextEntry -Archive $archive -EntryPath 'word/document.xml' -Content (Get-DocumentXml -DocumentDefinition $DocumentDefinition)
      Write-ZipTextEntry -Archive $archive -EntryPath 'word/_rels/document.xml.rels' -Content (Get-DocumentRelsXml)
      Write-ZipTextEntry -Archive $archive -EntryPath 'word/styles.xml' -Content (Get-StylesXml)
      Write-ZipTextEntry -Archive $archive -EntryPath 'word/settings.xml' -Content (Get-SettingsXml)
      Write-ZipTextEntry -Archive $archive -EntryPath 'word/webSettings.xml' -Content (Get-WebSettingsXml)
    } finally {
      $archive.Dispose()
    }
  } finally {
    $fileStream.Dispose()
  }

  return $absoluteTargetPath
}

$documentDefinition = Get-DocumentDefinition -JsonPath $DocJsonPath -JsonBase64Utf8 $DocJsonBase64Utf8 -DocumentTitle $Title -DocumentParagraphs $Paragraphs
$savedPath = New-DocxFromDefinition -DocumentDefinition $documentDefinition -TargetPath $OutputPath
Write-Output "Created DOCX: $savedPath"
