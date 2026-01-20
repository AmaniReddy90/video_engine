Write-Host "Checking system prerequisites..."
$checks = @(
  @{ Name = "Rust"; Command = "rustc --version" },
  @{ Name = "Node"; Command = "node --version" },
  @{ Name = "npm"; Command = "npm --version" },
  @{ Name = "Python"; Command = "python --version" }
)

foreach ($check in $checks) {
  try {
    $output = Invoke-Expression $check.Command
    Write-Host "$($check.Name): $output"
  } catch {
    Write-Host "$($check.Name): MISSING"
  }
}

Write-Host "Doctor complete."
