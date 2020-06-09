param(
    [string]$DestinationPath="pass.keypirinha-package"
)

$ErrorActionPreference = "Stop"

$zipdest = "pass.zip"

Compress-Archive -DestinationPath $zipdest -Path src\*, LICENSE -Update
mv $zipdest $DestinationPath -Force
