Set-Location "E:/project/workspace/myrepo/quant-atlas/docs"

$map = @{
    "01_" = "01_Requirements"
    "02_" = "02_Architecture"
    "03_" = "03_Functional"
    "04_" = "04_Testing"
    "05_" = "05_Deployment"
    "06_" = "06_DEPLOYMENT"
    "07_" = "07_REFACTORING"
    "08_" = "08_ANALYTICS"
    "09_" = "09_GRAPH"
    "04_UI_" = "04_UI"
}

foreach ($prefix in $map.Keys) {
    $target = $map[$prefix]
    Get-ChildItem -File -Filter "$prefix*.md" | ForEach-Object {
        $src = $_.FullName
        $dest = Join-Path $target $_.Name
        git mv $src $dest
    }
}
