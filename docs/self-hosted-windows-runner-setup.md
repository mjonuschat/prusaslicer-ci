# Self-Hosted Windows Runner Setup

Guide to setting up a Windows VM as a GitHub Actions self-hosted runner for PrusaSlicer (BOSS) builds.

## Requirements

- **OS:** Windows Server 2025 Standard (Core) or Windows 11 Pro
- **CPU:** 4 cores / 8 threads minimum (avoid over-provisioning — PCH compilation needs ~2 GB per thread)
- **RAM:** 16 GB minimum
- **Disk:** 64 GB (thin provisioned)
- **Network:** Internet access for package downloads and GitHub connectivity

> **Sizing note:** 4c/8t with 16 GB gives 2 GB per compilation thread, which is sufficient for MSVC with `-Zm520` PCH. More cores without proportionally more RAM causes PCH out-of-memory errors (C3859).

## OS Installation

1. Install Windows Server 2025 Standard **without** "Desktop Experience" (Core mode)
2. Set Administrator password via `sconfig`
3. Disable firewall (CI runner, not internet-facing):
   ```powershell
   Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled False
   ```

## SSH Access

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
New-ItemProperty -Path "HKLM:\SOFTWARE\OpenSSH" -Name DefaultShell -Value "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" -PropertyType String -Force
```

For key-based auth (admin users use a special file):
```powershell
Set-Content -Path "C:\ProgramData\ssh\administrators_authorized_keys" -Value "ssh-ed25519 AAAA... your-key"
icacls "C:\ProgramData\ssh\administrators_authorized_keys" /inheritance:r /grant "Administrators:F" /grant "SYSTEM:F"
Restart-Service sshd
```

## Build Tools Installation

### Package Manager
```powershell
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
```

### Packages
```powershell
choco install -y git cmake --version=3.31.6 ninja strawberryperl python3 innosetup pwsh 7zip gzip
```

> **CMake version:** Use 3.31.x, not 4.x. CMake 4.x removed compatibility with `cmake_minimum_required < 3.5`, breaking several dependencies.

> **Python 3** is required by the z3 dependency's configure step.

### CMake PATH Order

CMake 3.31 must come before Strawberry Perl's bundled cmake 3.29 on PATH. Strawberry's cmake defaults to gcc; we need cmake to find MSVC via vcvars.

```powershell
$currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($currentPath -notmatch "Program Files\\CMake\\bin") {
    $newPath = "C:\Program Files\CMake\bin;" + $currentPath
    [Environment]::SetEnvironmentVariable("Path", $newPath, "Machine")
}
```

Verify after opening a new session:
```
> where cmake
C:\Program Files\CMake\bin\cmake.exe
C:\Strawberry\c\bin\cmake.exe

> cmake --version
cmake version 3.31.6
```

### Visual Studio Build Tools

Install the base Build Tools (spawns background installer):
```powershell
Invoke-WebRequest -Uri "https://aka.ms/vs/17/release/vs_buildtools.exe" -OutFile C:\vs_buildtools.exe
Start-Process -FilePath C:\vs_buildtools.exe -ArgumentList "--add","Microsoft.VisualStudio.Workload.VCTools","--includeRecommended","--quiet","--norestart" -Wait -NoNewWindow
```

Wait for the background installer to finish:
```powershell
while (Get-Process | Where-Object { $_.Name -match "setup|vs_" }) { Start-Sleep 5 }
```

Add ATL support (needed for `atlbase.h`):
```powershell
& "C:\Program Files (x86)\Microsoft Visual Studio\Installer\setup.exe" modify `
    --installPath "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools" `
    --add Microsoft.VisualStudio.Component.VC.ATL `
    --passive --norestart --force
```

Wait for completion and verify:
```powershell
while (Get-Process | Where-Object { $_.Name -match "setup|vs_" }) { Start-Sleep 5 }
Test-Path "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Tools\MSVC\*\atlmfc\include\atlbase.h"
# Should return True
```

Reboot after VS Build Tools installation:
```powershell
Restart-Computer -Force
```

## Disable Windows Defender

```powershell
Set-MpPreference -DisableRealtimeMonitoring $true
New-Item -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender" -Force | Out-Null
New-ItemProperty -Path "HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender" -Name DisableAntiSpyware -Value 1 -PropertyType DWORD -Force
```

## Verify Build

Clone and do a test build:

```cmd
call "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
git clone --depth 1 --branch boss https://github.com/mjonuschat/PrusaSlicer.git C:\PrusaSlicer
cd C:\PrusaSlicer
cmake -P build.cmake
```

Expected: ~30 min deps + ~15 min slicer on 4c/8t/16GB.

## Environment Protection

The Windows build workflow requires a `self-hosted-approval` environment on the **PrusaSlicer repo** (not this CI repo). This gates PR builds behind manual reviewer approval to prevent untrusted fork code from running on the self-hosted runner.

1. Go to PrusaSlicer repo **Settings** > **Environments** > **New environment**
2. Name: `self-hosted-approval`
3. Enable **Required reviewers** and add trusted maintainers
4. Save protection rules

Push-triggered builds (to `boss` and `release/*`) bypass this gate automatically.

## GitHub Actions Runner Agent

### Generate Registration Token

Go to the PrusaSlicer repo **Settings** > **Actions** > **Runners** > **New self-hosted runner**. The page shows a registration token in the configure step. The token expires in 1 hour.

### Download and Extract

```powershell
mkdir C:\actions-runner
Invoke-WebRequest -Uri "https://github.com/actions/runner/releases/latest/download/actions-runner-win-x64-2.323.0.zip" -OutFile C:\actions-runner\runner.zip
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory("C:\actions-runner\runner.zip", "C:\actions-runner")
Remove-Item C:\actions-runner\runner.zip
```

> Check [actions/runner releases](https://github.com/actions/runner/releases) for the latest version.

### Configure

```cmd
cd C:\actions-runner
config.cmd --url https://github.com/mjonuschat/PrusaSlicer --token <TOKEN> --name gha-boss-windows --labels self-hosted,windows,x64 --unattended
```

### Install as Windows Service

```powershell
sc.exe create actions.runner.mjonuschat-PrusaSlicer.gha-boss-windows binPath= "C:\actions-runner\bin\RunnerService.exe" start= auto
sc.exe start actions.runner.mjonuschat-PrusaSlicer.gha-boss-windows
```

Verify the service is running:
```powershell
sc.exe query actions.runner.mjonuschat-PrusaSlicer.gha-boss-windows
# STATE should be RUNNING
```

Verify on GitHub: go to **Settings** > **Actions** > **Runners** — the runner should show as **Idle** (green dot).

### Reconfiguring

To change the runner name or labels, stop the service, remove, reconfigure, and reinstall:

```powershell
sc.exe stop actions.runner.mjonuschat-PrusaSlicer.gha-boss-windows
sc.exe delete actions.runner.mjonuschat-PrusaSlicer.gha-boss-windows
```

```cmd
cd C:\actions-runner
config.cmd remove --token <TOKEN>
config.cmd --url https://github.com/mjonuschat/PrusaSlicer --token <NEW_TOKEN> --name <new-name> --labels self-hosted,windows,x64 --unattended
```

Then recreate the service with the new name.

## Troubleshooting

### `gcc.exe: error: /FS: linker input file not found`
CMake is using Strawberry Perl's gcc instead of MSVC. Ensure:
1. `vcvars64.bat` was called before the build
2. CMake 3.31 is first on PATH (before Strawberry's cmake 3.29)

### `fatal error C3859: Failed to create virtual memory for PCH`
Too many parallel compilations for available RAM. Reduce VM cores or add RAM. Target ~2 GB per thread minimum.

### `fatal error C1041: cannot open program database`
Ninja + MSVC parallel PDB writes. The toolchain file (`cmake/toolchain-msvc-ninja.cmake`) appends `/FS` via `CMAKE_C_FLAGS_INIT` to fix this. Ensure it's referenced in `CMakePresets.json` and `build.cmake`.

### `Could NOT find Iconv`
CMake can't find Strawberry Perl's iconv. Ensure Strawberry is installed (`choco install strawberryperl`) and `C:\Strawberry\c\bin` is on PATH.

### CGAL `gmpxx.h` errors
If `CGAL_WITH_GMPXX` is incorrectly detected as ON, the `/FS` flags may be clobbering MSVC defaults. Ensure `/FS` is added via the toolchain file's `FLAGS_INIT` (not via `CMAKE_CXX_FLAGS` in presets).

### `atlbase.h: No such file or directory`
ATL component not installed. Add `Microsoft.VisualStudio.Component.VC.ATL` to the VS Build Tools installation.
