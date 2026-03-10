; VOK Downloader — Inno Setup Script
; Run from project root: ISCC resources\installer\script_inno.iss /DMyAppVersion=0.1.9
; In CI, version and output dir are passed via /D defines.

#ifndef MyAppVersion
  #define MyAppVersion "0.1.0"
#endif

#define MyAppName "VOK Downloader"
#define MyAppPublisher "VOK"
#define MyAppURL "https://github.com/k10978311-ai/VOK-Get"
#define MyAppExeName "VOK.exe"

[Setup]
AppId={{D268B6A1-50E6-4A03-9099-3C955452D4F5}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
OutputDir=dist
OutputBaseFilename=VOK-v{#MyAppVersion}-Windows-x86_64-Setup
SetupIconFile=resources\icon.ico
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\VOK\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\VOK\_internal\*"; DestDir: "{app}\_internal"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

