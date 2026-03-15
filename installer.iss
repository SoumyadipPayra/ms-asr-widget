; Inno Setup script for ASR Widget
; Requires Inno Setup 6 — https://jrsoftware.org/isinfo.php

#define AppName "ASR Widget"
#define AppVersion "0.1.0"
#define AppPublisher "ASR Widget"
#define AppExeName "ASRWidget.exe"

[Setup]
AppId={{A5B7C8D9-E0F1-4A2B-8C3D-5E6F7A8B9C0D}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
OutputDir=dist
OutputBaseFilename=ASRWidgetSetup-{#AppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayIcon={app}\{#AppExeName}
ArchitecturesAllowed=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"
Name: "startup"; Description: "Start with &Windows"; GroupDescription: "Startup:"

[Files]
Source: "dist\ASRWidget\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; \
    ValueType: string; ValueName: "{#AppName}"; \
    ValueData: """{app}\{#AppExeName}"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
var
  ServerPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  { Custom page: ASR Server Endpoint }
  ServerPage := CreateInputQueryPage(
    wpSelectTasks,
    'ASR Server Configuration',
    'Enter the WebSocket URL of your ASR gateway server.',
    'The widget will stream audio to this server for transcription.'
  );
  ServerPage.Add('Server URL:', False);
  ServerPage.Values[0] := 'ws://localhost:8765';
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = ServerPage.ID then
  begin
    if Trim(ServerPage.Values[0]) = '' then
    begin
      MsgBox('Please enter the ASR server URL.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;

procedure WriteConfig;
var
  ConfigDir: String;
  ConfigFile: String;
  Lines: TArrayOfString;
begin
  ConfigDir := ExpandConstant('{userappdata}\asr-widget');
  ForceDirectories(ConfigDir);

  ConfigFile := ConfigDir + '\config.toml';

  SetArrayLength(Lines, 13);
  Lines[0]  := '[gateway]';
  Lines[1]  := 'url = "' + ServerPage.Values[0] + '"';
  Lines[2]  := '';
  Lines[3]  := '[audio]';
  Lines[4]  := 'sample_rate = 16000';
  Lines[5]  := 'chunk_duration_ms = 100';
  Lines[6]  := '';
  Lines[7]  := '[hotkey]';
  Lines[8]  := 'combination = "<ctrl>+<shift>+<space>"';
  Lines[9]  := 'mode = "toggle"';
  Lines[10] := '';
  Lines[11] := '[ui]';
  Lines[12] := 'size = 44';

  SaveStringsToUTF8File(ConfigFile, Lines, False);

  { Write setup marker so the app skips the first-run wizard }
  SaveStringToFile(ConfigDir + '\.setup_done', 'setup_complete' + #13#10, False);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    WriteConfig;
end;
