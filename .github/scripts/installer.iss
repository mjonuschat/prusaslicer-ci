; PrusaSlicer (BOSS) Inno Setup installer script
;
; Required defines (pass via /D on command line):
;   BuildDir    - Path to the Ninja build output (e.g., build\src)
;   Version     - Version string (e.g., 2.9.4+BOSS)
;   VCRedistCRT - Path to VC++ CRT DLLs (e.g., %VCToolsRedistDir%\x64\Microsoft.VC143.CRT)
;   OutputDir   - Directory for the output installer .exe

#ifndef BuildDir
  #error "BuildDir must be defined via /DBuildDir=..."
#endif
#ifndef Version
  #error "Version must be defined via /DVersion=..."
#endif
#ifndef VCRedistCRT
  #error "VCRedistCRT must be defined via /DVCRedistCRT=..."
#endif
#ifndef OutputDir
  #define OutputDir "."
#endif

[Setup]
AppName=PrusaSlicer+BOSS
AppVersion={#Version}
AppVerName=PrusaSlicer {#Version}
AppPublisher=mjonuschat
AppPublisherURL=https://github.com/mjonuschat/PrusaSlicer
AppSupportURL=https://github.com/mjonuschat/PrusaSlicer/issues
DefaultDirName={autopf}\PrusaSlicer+BOSS
DefaultGroupName=PrusaSlicer+BOSS
UninstallDisplayIcon={app}\PrusaSlicer.exe
OutputDir={#OutputDir}
OutputBaseFilename=PrusaSlicer-Installer-{#Version}
Compression=lzma2/ultra64
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile={#BuildDir}\..\..\LICENSE
SetupIconFile={#BuildDir}\..\..\resources\icons\PrusaSlicer.ico
WizardStyle=modern
DisableProgramGroupPage=yes
CloseApplications=force

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "czech"; MessagesFile: "compiler:Languages\Czech.isl"
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "german"; MessagesFile: "compiler:Languages\German.isl"
Name: "italian"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "polish"; MessagesFile: "compiler:Languages\Polish.isl"

[Files]
; Main executable. 3.0 unified the GUI, CLI, and G-code viewer into one
; binary (slic3r-app-launcher, staged here as PrusaSlicer.exe); the viewer
; is a --gcodeviewer flag, not a separate executable.
Source: "{#BuildDir}\PrusaSlicer.exe"; DestDir: "{app}"; Flags: ignoreversion
; Shared libraries
Source: "{#BuildDir}\OCCTWrapper.dll"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#BuildDir}\WebView2Loader.dll"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#BuildDir}\libgmp-10.dll"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "{#BuildDir}\libmpfr-4.dll"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
; VC++ runtime — sourced directly from the MSVC toolchain that compiled the code
Source: "{#VCRedistCRT}\vcruntime140.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#VCRedistCRT}\vcruntime140_1.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#VCRedistCRT}\msvcp140.dll"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#VCRedistCRT}\msvcp140_codecvt_ids.dll"; DestDir: "{app}"; Flags: ignoreversion
; Mesa software OpenGL fallback
Source: "{#BuildDir}\mesa\opengl32.dll"; DestDir: "{app}\mesa"; Flags: ignoreversion skipifsourcedoesntexist
; Resources
Source: "{#BuildDir}\resources\*"; DestDir: "{app}\resources"; Flags: ignoreversion recursesubdirs createallsubdirs
; License
Source: "{#BuildDir}\..\..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\PrusaSlicer+BOSS"; Filename: "{app}\PrusaSlicer.exe"
Name: "{group}\PrusaSlicer+BOSS G-code Viewer"; Filename: "{app}\PrusaSlicer.exe"; Parameters: "--gcodeviewer"
Name: "{group}\Uninstall PrusaSlicer+BOSS"; Filename: "{uninstallexe}"
Name: "{autodesktop}\PrusaSlicer+BOSS"; Filename: "{app}\PrusaSlicer.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Run]
Filename: "{app}\PrusaSlicer.exe"; Description: "{cm:LaunchProgram,PrusaSlicer+BOSS}"; Flags: nowait postinstall skipifsilent
