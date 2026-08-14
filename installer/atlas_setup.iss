; ===========================================================================
;  Atlas — MT5 Supervisor — Inno Setup script
;  Output:  Atlas_Setup.exe   (per-user installer — no Administrator)
;  Install root: %LOCALAPPDATA%\Atlas
;  Runtime: tray launcher (no Windows services / NSSM)
;  Build:   Run build.bat (downloads payload deps + invokes ISCC.exe)
; ===========================================================================
#define MyAppName      "Atlas"
#ifndef MyAppVersion
  #define MyAppVersion "0.3.0"
#endif
#define MyAppPublisher "Quant.Supervise"
#define MyAppURL       "https://quant.supervise"
#define InstallRoot    "{localappdata}\Atlas"

[Setup]
AppId={{B8A21F36-3D72-4F1B-9F2A-1A8E2C0D77E1}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={#InstallRoot}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE.txt
OutputBaseFilename=Atlas_Setup
OutputDir=dist
SetupIconFile=icons\atlas.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Per-user install — no UAC / Administrator prompt.
PrivilegesRequired=lowest
UsePreviousAppDir=no
CloseApplications=yes
RestartApplications=no
ArchitecturesInstallIn64BitMode=x64compatible
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\icons\atlas.ico
UninstallDisplayName={#MyAppName} {#MyAppVersion}
VersionInfoVersion={#MyAppVersion}.0
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription=Atlas MT5 Supervisor Installer
VersionInfoCopyright=© 2026 {#MyAppPublisher}

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "pt"; MessagesFile: "compiler:Languages\Portuguese.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut for Atlas"; GroupDescription: "Shortcuts:"
Name: "startmenu";   Description: "Create Start Menu shortcuts"; GroupDescription: "Shortcuts:"
Name: "startup";     Description: "Start Atlas when I sign in to Windows"; GroupDescription: "Startup:"; Flags: unchecked
Name: "openbrowser"; Description: "Open the dashboard in the browser after install"; GroupDescription: "Post-install:"; Flags: checkedonce

[Files]
; -- Python embeddable runtime (Atlas\python\) ----------------------------
Source: "payload\python\*";          DestDir: "{app}\python";         Flags: recursesubdirs ignoreversion

; -- Backend source --------------------------------------------------------
Source: "payload\backend\*";         DestDir: "{app}\backend";        Flags: recursesubdirs ignoreversion

; -- Bridge source ---------------------------------------------------------
Source: "payload\bridge\*";          DestDir: "{app}\bridge";         Flags: recursesubdirs ignoreversion

; -- Frontend (pre-built React) -------------------------------------------
Source: "payload\frontend_build\*";  DestDir: "{app}\frontend_build"; Flags: recursesubdirs ignoreversion

; -- Operation scripts (tray launcher — no NSSM / Windows services) ------
Source: "scripts\_detect_env.bat";         DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\atlas_launcher.py";       DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\start_atlas_app.bat";     DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\start_atlas.bat";         DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\stop_atlas.bat";          DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\open_dashboard.bat";      DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\healthcheck.bat";         DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\bootstrap_pip.bat";       DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\install_deps.bat";        DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\apply_restart.bat";       DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\configure_atlas.py";      DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\configure_mt5.bat";       DestDir: "{app}\scripts"; Flags: ignoreversion

; -- Icons & misc ----------------------------------------------------------
Source: "icons\atlas.ico";  DestDir: "{app}\icons";  Flags: ignoreversion
Source: "LICENSE.txt";      DestDir: "{app}";        Flags: ignoreversion
Source: "README_INSTALL.txt"; DestDir: "{app}";      Flags: ignoreversion

[Dirs]
Name: "{app}\data"
Name: "{app}\logs"

[InstallDelete]
; Clean code tree on upgrade (preserve {app}\data and {app}\logs).
Type: filesandordirs; Name: "{app}\backend"
Type: filesandordirs; Name: "{app}\bridge"
Type: filesandordirs; Name: "{app}\frontend_build"
Type: filesandordirs; Name: "{app}\python\Lib\site-packages"
Type: filesandordirs; Name: "{app}\python\Scripts"
Type: files;          Name: "{app}\backend\build_info.json"
; Drop legacy Windows-service leftovers from older builds.
Type: files; Name: "{app}\nssm.exe"
Type: files; Name: "{app}\scripts\install_services.bat"
Type: files; Name: "{app}\scripts\uninstall_services.bat"

[Icons]
Name: "{group}\Atlas";              Filename: "{app}\scripts\start_atlas_app.bat"; IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Atlas Dashboard";    Filename: "{app}\scripts\open_dashboard.bat";  IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Atlas Health Check"; Filename: "{app}\scripts\healthcheck.bat";     IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Stop Atlas";         Filename: "{app}\scripts\stop_atlas.bat";      IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Uninstall Atlas";    Filename: "{uninstallexe}"; Tasks: startmenu
Name: "{userdesktop}\Atlas";        Filename: "{app}\scripts\start_atlas_app.bat"; IconFilename: "{app}\icons\atlas.ico"; Tasks: desktopicon
; Optional sign-in auto-start (user Startup folder — not a Windows service).
Name: "{userstartup}\Atlas";        Filename: "{app}\scripts\start_atlas_app.bat"; IconFilename: "{app}\icons\atlas.ico"; Tasks: startup

[Run]
; 1) Install pip into embedded Python and pip-install backend + bridge deps
Filename: "{app}\scripts\bootstrap_pip.bat"; StatusMsg: "Setting up Python runtime..."; Flags: runhidden
Filename: "{app}\scripts\install_deps.bat";  StatusMsg: "Installing Python dependencies (this may take a few minutes)..."; Flags: runhidden

; 2) Write .env from the wizard answers (or restore previous config).
Filename: "{app}\python\python.exe"; Parameters: """{app}\scripts\configure_atlas.py"" --answers ""{tmp}\atlas_mt5_answers.json"" --non-interactive --backend-dir ""{app}\backend"" --bridge-dir ""{app}\bridge"" --data-dir ""{app}\data"""; WorkingDir: "{app}"; StatusMsg: "Saving MetaTrader 5 configuration..."; Flags: runhidden

; 3) Start Atlas as a normal tray application (no Windows services).
Filename: "{app}\scripts\start_atlas_app.bat"; StatusMsg: "Starting Atlas..."; Flags: nowait

; 4) Optional: open the dashboard URL (launcher also opens once when healthy).
Filename: "{app}\scripts\open_dashboard.bat"; StatusMsg: "Opening dashboard..."; Tasks: openbrowser; Flags: nowait skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\python\Lib\site-packages"

[Code]
var
  MT5Page: TInputQueryWizardPage;
  MT5Ready: Boolean;

procedure InitializeWizard();
var
  AnswersSrc, AnswersDst: String;
begin
  MT5Ready := False;
  MT5Page := CreateInputQueryPage(wpSelectTasks,
    'MetaTrader 5 Account',
    'Connect Atlas to your MetaTrader 5 account',
    'Enter your MT5 login details so Atlas can connect right after setup.' + #13#10 +
    'They are stored locally on this computer only and are never sent' + #13#10 +
    'anywhere by Atlas. Leave all fields blank to configure later from the' + #13#10 +
    'dashboard Settings page.');
  MT5Page.Add('MT5 Login (number):', False);
  MT5Page.Add('MT5 Password:', True);
  MT5Page.Add('MT5 Server / Broker (e.g. Darwinex-Live):', False);
  MT5Page.Add('MT5 terminal path (optional; blank = auto-detect):', False);

  AnswersSrc := ExpandConstant('{param:ANSWERS|}');
  if (AnswersSrc <> '') and FileExists(AnswersSrc) then
  begin
    AnswersDst := ExpandConstant('{tmp}\atlas_mt5_answers.json');
    if CopyFile(AnswersSrc, AnswersDst, False) then
      MT5Ready := True;
  end
  else
  begin
    MT5Page.Values[0] := ExpandConstant('{param:MT5LOGIN|}');
    MT5Page.Values[1] := ExpandConstant('{param:MT5PASSWORD|}');
    MT5Page.Values[2] := ExpandConstant('{param:MT5SERVER|}');
    MT5Page.Values[3] := ExpandConstant('{param:MT5PATH|}');
  end;
end;

function JsonEscape(const S: String): String;
var
  I: Integer;
  C: Char;
  R: String;
begin
  R := '';
  for I := 1 to Length(S) do
  begin
    C := S[I];
    if (C = '\') or (C = '"') then
      R := R + '\' + C
    else if C = #13 then
      R := R + '\r'
    else if C = #10 then
      R := R + '\n'
    else
      R := R + C;
  end;
  Result := R;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  Login, Pass, Server, TermPath, Json, AnswersFile: String;
begin
  Result := True;
  if (MT5Page <> nil) and (CurPageID = MT5Page.ID) then
  begin
    Login    := Trim(MT5Page.Values[0]);
    Pass     := MT5Page.Values[1];
    Server   := Trim(MT5Page.Values[2]);
    TermPath := Trim(MT5Page.Values[3]);
    MT5Ready := False;

    if (Login = '') and (Pass = '') and (Server = '') then
    begin
      Exit;
    end;

    if (Login = '') or (Pass = '') or (Server = '') then
    begin
      MsgBox('Please fill in MT5 Login, Password and Server, or clear all' + #13#10 +
             'three fields to configure MetaTrader 5 later.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if StrToIntDef(Login, -1) < 0 then
    begin
      MsgBox('MT5 Login must be a number.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    Json := '{"login":"' + JsonEscape(Login) +
            '","password":"' + JsonEscape(Pass) +
            '","server":"' + JsonEscape(Server) +
            '","terminal_path":"' + JsonEscape(TermPath) +
            '","bridge_port":8002}';
    AnswersFile := ExpandConstant('{tmp}\atlas_mt5_answers.json');
    if SaveStringToFile(AnswersFile, Json, False) then
      MT5Ready := True
    else
      MsgBox('Could not save the MT5 configuration temporarily. You can set' + #13#10 +
             'it up later from the dashboard Settings page.', mbInformation, MB_OK);
  end;
end;

function ServiceRegistered(const Name: String): Boolean;
var
  ResultCode: Integer;
begin
  // sc query works without elevation. Exit code 0 = service exists;
  // 1060 = ERROR_SERVICE_DOES_NOT_EXIST.
  Result :=
    Exec('sc.exe', 'query "' + Name + '"', '', SW_HIDE, ewWaitUntilTerminated, ResultCode)
    and (ResultCode = 0);
end;

function LegacyAtlasServicesPresent(): Boolean;
begin
  Result := ServiceRegistered('AtlasBackend') or ServiceRegistered('AtlasBridge');
end;

procedure KillBundledPythonAt(const Root: String);
var
  ResultCode: Integer;
  PyDll: String;
begin
  if (Root = '') or (not DirExists(Root)) then Exit;
  PyDll := Root + '\python\python311.dll';
  if not FileExists(PyDll) then Exit;
  // User-owned processes only — never elevates, never touches SCM / nssm.
  Exec('taskkill.exe',
       '/F /FI "IMAGENAME eq python.exe" /FI "MODULES eq ' + PyDll + '"',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('taskkill.exe',
       '/F /FI "IMAGENAME eq pythonw.exe" /FI "MODULES eq ' + PyDll + '"',
       '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure KillUserAtlasProcesses();
begin
  // Current per-user install.
  KillBundledPythonAt(ExpandConstant('{app}'));
  // Leftover interpreters under legacy Program Files trees (best-effort, no UAC).
  KillBundledPythonAt(ExpandConstant('{commonpf64}\Atlas'));
  KillBundledPythonAt(ExpandConstant('{commonpf}\Atlas'));
  KillBundledPythonAt(ExpandConstant('{pf}\Atlas'));
end;

procedure RemoveLegacyServicesDirect();
var
  ResultCode: Integer;
begin
  // Prefer sc.exe — do NOT launch nssm.exe (its manifest triggers unexplained UAC).
  Exec('net.exe', 'stop AtlasBackend', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('net.exe', 'stop AtlasBridge',  '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('sc.exe', 'delete AtlasBackend', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('sc.exe', 'delete AtlasBridge',  '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

function RemoveLegacyServicesElevated(): Boolean;
var
  Bat: String;
  ErrorCode: Integer;
  Lines: String;
begin
  // One-shot elevated helper. No nssm.exe — only net/sc against the two service names.
  Bat := ExpandConstant('{tmp}\atlas_remove_legacy_services.bat');
  Lines :=
    '@echo off' + #13#10 +
    'net stop AtlasBackend >nul 2>nul' + #13#10 +
    'net stop AtlasBridge >nul 2>nul' + #13#10 +
    'sc delete AtlasBackend >nul 2>nul' + #13#10 +
    'sc delete AtlasBridge >nul 2>nul' + #13#10 +
    'exit /b 0' + #13#10;
  if not SaveStringToFile(Bat, Lines, False) then
  begin
    Result := False;
    Exit;
  end;
  // 'runas' shows the standard Windows consent UI. Returns False if the user cancels.
  Result := ShellExec('runas', Bat, '', '', SW_HIDE, ewWaitUntilTerminated, ErrorCode);
end;

procedure WarnLegacyServicesSkipped();
begin
  MsgBox(
    'Atlas will continue installing for your user account' + #13#10 +
    '(' + ExpandConstant('{localappdata}\Atlas') + ').' + #13#10 + #13#10 +
    'The older Windows services (AtlasBackend / AtlasBridge) were NOT removed.' + #13#10 +
    'They may still use ports 8001/8002.' + #13#10 + #13#10 +
    'Please uninstall the old Program Files copy of Atlas from' + #13#10 +
    'Windows Settings → Apps (or Add/Remove Programs), then start the new Atlas.',
    mbInformation, MB_OK);
end;

procedure MaybeRemoveLegacyServices();
begin
  if not LegacyAtlasServicesPresent() then
    Exit;  // Fresh / already-migrated machine: never touch SCM, never UAC.

  if IsAdminInstallMode then
  begin
    RemoveLegacyServicesDirect();
    Exit;
  end;

  if MsgBox(
       'An older Atlas install registered Windows services' + #13#10 +
       '(AtlasBackend / AtlasBridge), usually under Program Files.' + #13#10 + #13#10 +
       'Windows will ask for administrator permission ONLY to stop and' + #13#10 +
       'remove those old services. The new Atlas installs per-user and' + #13#10 +
       'does not use Windows services.' + #13#10 + #13#10 +
       'Allow removal of the old services now?',
       mbConfirmation, MB_YESNO) = IDYES then
  begin
    if not RemoveLegacyServicesElevated() then
      WarnLegacyServicesSkipped();
  end
  else
    WarnLegacyServicesSkipped();
end;

procedure StopAtlasProcesses();
begin
  // 1) Always: stop the per-user tray app / bundled python (no elevation).
  KillUserAtlasProcesses();
  // 2) Only if legacy NSSM-era services still exist: explained UAC, or skip.
  MaybeRemoveLegacyServices();
  Sleep(1000);
end;

function InitializeSetup(): Boolean;
begin
  Result := True;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopAtlasProcesses();
  Result := '';
end;

function InitializeUninstall(): Boolean;
begin
  // Stop tray app before files are removed (no SCM/nssm from the unelevated path).
  KillUserAtlasProcesses();
  // Optional: clean legacy services on uninstall with the same explained prompt.
  MaybeRemoveLegacyServices();
  DeleteFile(ExpandConstant('{userstartup}\Atlas.lnk'));
  Result := True;
end;
