# P2P-CI System - PowerShell Helper Script
# Usage: .\run.ps1 <command>

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

switch ($Command) {
    "server" {
        Write-Host "Starting Central Index Server on port 7734..." -ForegroundColor Green
        python server.py
    }
    "peer" {
        Write-Host "Starting Peer with default RFC directory..." -ForegroundColor Green
        python peer.py
    }
    "peer-a" {
        Write-Host "Starting Peer A with rfc_a directory..." -ForegroundColor Green
        python peer.py -d rfc_a
    }
    "peer-b" {
        Write-Host "Starting Peer B with rfc_b directory..." -ForegroundColor Green
        python peer.py -d rfc_b
    }
    "peer-empty" {
        Write-Host "Starting Peer with empty RFC directory..." -ForegroundColor Green
        if (-not (Test-Path "rfc_empty")) {
            New-Item -ItemType Directory -Path "rfc_empty" | Out-Null
        }
        python peer.py -d rfc_empty
    }
    "clean" {
        Write-Host "Cleaning up temporary files and downloaded RFCs..." -ForegroundColor Yellow
        if (Test-Path "rfc_empty") { Remove-Item -Recurse -Force "rfc_empty" }
        if (Test-Path "__pycache__") { Remove-Item -Recurse -Force "__pycache__" }
        # Remove downloaded files from rfc_a (keep rfc123.txt)
        Get-ChildItem -Path "rfc_a" -File | Where-Object { $_.Name -ne "rfc123.txt" } | Remove-Item -Force -ErrorAction SilentlyContinue
        # Remove downloaded files from rfc_b (keep rfc2345.txt)
        Get-ChildItem -Path "rfc_b" -File | Where-Object { $_.Name -ne "rfc2345.txt" } | Remove-Item -Force -ErrorAction SilentlyContinue
        Write-Host "Done." -ForegroundColor Green
    }
    "help" {
        Write-Host ""
        Write-Host "P2P-CI System - PowerShell Commands" -ForegroundColor Cyan
        Write-Host "====================================" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Usage: .\run.ps1 <command>"
        Write-Host ""
        Write-Host "Commands:"
        Write-Host "  server      - Start the central index server (port 7734)"
        Write-Host "  peer        - Start a peer client (uses ./rfc directory)"
        Write-Host "  peer-a      - Start Peer A (uses ./rfc_a, has RFC 123)"
        Write-Host "  peer-b      - Start Peer B (uses ./rfc_b, has RFC 2345)"
        Write-Host "  peer-empty  - Start a peer with empty RFC directory"
        Write-Host "  clean       - Remove temporary files and downloaded RFCs"
        Write-Host "  help        - Show this help message"
        Write-Host ""
        Write-Host "Demo workflow:" -ForegroundColor Yellow
        Write-Host "  Terminal 1: .\run.ps1 server"
        Write-Host "  Terminal 2: .\run.ps1 peer-a"
        Write-Host "  Terminal 3: .\run.ps1 peer-b"
        Write-Host ""
    }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Run '.\run.ps1 help' for usage information."
    }
}
