[Setup]
AppId=LanternLocalDiagnostics
AppName=Lantern Diagnostics
AppVersion=0.1.0
DefaultDirName={localappdata}\Programs\Lantern
DefaultGroupName=Lantern
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Lantern-Setup-0.1.0
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes

[Files]
Source: "..\dist\Lantern\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{userprograms}\Lantern Diagnostics"; Filename: "{app}\Lantern.exe"
Name: "{userdesktop}\Lantern Diagnostics"; Filename: "{app}\Lantern.exe"

[Run]
Filename: "{app}\Lantern.exe"; Description: "Open Lantern Diagnostics"; Flags: nowait postinstall skipifsilent
