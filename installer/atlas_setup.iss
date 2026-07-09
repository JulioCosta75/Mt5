; ===========================================================================
;  Atlas — MT5 Supervisor — Inno Setup script
;  Output:  Atlas_Setup.exe   (single-file installer for Windows VPS)
;  Build:   Run build.bat (downloads payload deps + invokes ISCC.exe)
; ===========================================================================
#define MyAppName      "Atlas"
#ifndef MyAppVersion
  #define MyAppVersion "0.3.0"
#endif
#define MyAppPublisher "Quant.Supervise"
#define MyAppURL       "https://quant.supervise"
#define MyAppExeName   "Atlas Wizard.exe"
#define InstallRoot    "{autopf}\Atlas"

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
PrivilegesRequired=admin
; -- Close the Atlas Wizard if it is running so its files can be replaced.
CloseApplications=yes
RestartApplications=no
; -- Always deploy on top of a clean tree (see [InstallDelete]).
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
Name: "desktopicon"; Description: "Create a desktop shortcut for the Atlas dashboard"; GroupDescription: "Shortcuts:"
Name: "startmenu";   Description: "Create Start Menu shortcuts"; GroupDescription: "Shortcuts:"
Name: "installsvc";  Description: "Install Atlas as Windows Services (auto-start on boot)"; GroupDescription: "Services:"; Flags: checkedonce
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

; -- NSSM service manager (single .exe) ----------------------------------
Source: "payload\nssm.exe";          DestDir: "{app}";                Flags: ignoreversion

; -- Service & operation scripts -----------------------------------------
Source: "scripts\_detect_env.bat";         DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\install_services.bat";    DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\uninstall_services.bat";  DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\start_atlas.bat";         DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\stop_atlas.bat";          DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\open_dashboard.bat";      DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\healthcheck.bat";         DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\bootstrap_pip.bat";       DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\install_deps.bat";        DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\apply_restart.bat";       DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\configure_atlas.py";     DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\configure_mt5.bat";       DestDir: "{app}\scripts"; Flags: ignoreversion

; -- Icons & misc ----------------------------------------------------------
Source: "icons\atlas.ico";  DestDir: "{app}\icons";  Flags: ignoreversion
Source: "LICENSE.txt";      DestDir: "{app}";        Flags: ignoreversion
Source: "README_INSTALL.txt"; DestDir: "{app}";      Flags: ignoreversion

[Dirs]
Name: "{app}\data";  Permissions: users-modify
Name: "{app}\logs";  Permissions: users-modify

[InstallDelete]
; Guarantee a clean, reproducible deployment: remove the previous build's
; code and Python packages so the new version fully replaces the old one.
; (User data in {app}\data and logs in {app}\logs are preserved.)
Type: filesandordirs; Name: "{app}\backend"
Type: filesandordirs; Name: "{app}\bridge"
Type: filesandordirs; Name: "{app}\frontend_build"
Type: filesandordirs; Name: "{app}\python\Lib\site-packages"
Type: filesandordirs; Name: "{app}\python\Scripts"
Type: files;          Name: "{app}\backend\build_info.json"

[Icons]
Name: "{group}\Atlas Dashboard";    Filename: "{app}\scripts\open_dashboard.bat"; IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Atlas Health Check"; Filename: "{app}\scripts\healthcheck.bat";    IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Stop Atlas";         Filename: "{app}\scripts\stop_atlas.bat";     IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Start Atlas";        Filename: "{app}\scripts\start_atlas.bat";    IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Uninstall Atlas";    Filename: "{uninstallexe}"; Tasks: startmenu
Name: "{commondesktop}\Atlas Dashboard"; Filename: "{app}\scripts\open_dashboard.bat"; IconFilename: "{app}\icons\atlas.ico"; Tasks: desktopicon

[Run]
; 1) Install pip into embedded Python and pip-install backend + bridge deps
Filename: "{app}\scripts\bootstrap_pip.bat"; StatusMsg: "Setting up Python runtime..."; Flags: runhidden
Filename: "{app}\scripts\install_deps.bat";  StatusMsg: "Installing Python dependencies (this may take a few minutes)..."; Flags: runhidden

; 2) Write the .env files the services read. Uses the credentials entered
;    on the wizard page (if any); otherwise, on a reinstall/upgrade, it
;    restores the previously saved MT5 config so the bridge reconnects
;    automatically. A blank first-time install is a harmless no-op.
Filename: "{app}\python\python.exe"; Parameters: """{app}\scripts\configure_atlas.py"" --answers ""{tmp}\atlas_mt5_answers.json"" --non-interactive --backend-dir ""{app}\backend"" --bridge-dir ""{app}\bridge"" --data-dir ""{app}\data"""; WorkingDir: "{app}"; StatusMsg: "Saving MetaTrader 5 configuration..."; Flags: runhidden

; 3) Install services if user accepted
Filename: "{app}\scripts\install_services.bat"; StatusMsg: "Registering Atlas Windows Services..."; Tasks: installsvc; Flags: runhidden

; 4) Start the freshly installed build so the dashboard is live immediately.
;    The bridge picks up the .env written in step 2 and connects to MT5.
Filename: "{app}\scripts\start_atlas.bat"; StatusMsg: "Starting Atlas services..."; Tasks: installsvc; Flags: runhidden

[UninstallRun]
Filename: "{app}\scripts\uninstall_services.bat"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\python\Lib\site-packages"

[Code]
var
  MT5Page: TInputQueryWizardPage;
  MT5Ready: Boolean;

// Collect MT5 credentials on their own wizard page (after task selection).
procedure InitializeWizard();
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
end;

// Minimal JSON string escaper for the answers file.
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

// Validate the MT5 page and, when filled, write a temp answers file that
// the [Run] step feeds to configure_atlas.py.
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
      Exit;  // user chose to configure later

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

// ---------------------------------------------------------------------------
//  Stop + remove the Atlas services and any bundled python.exe left running,
//  BEFORE Inno deletes/copies files. This is what makes every install a clean,
//  reproducible deployment (fixes "dashboard still runs the previous version").
// ---------------------------------------------------------------------------
procedure StopAtlasServices();
var
  ResultCode: Integer;
  Nssm: String;
begin
  // 1) Graceful stop via the Windows Service Control Manager.
  Exec('net.exe', 'stop AtlasBackend', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('net.exe', 'stop AtlasBridge',  '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // 2) Remove the service definitions (NSSM if present, else sc.exe) so the
  //    new build re-registers them cleanly.
  Nssm := ExpandConstant('{app}\nssm.exe');
  if FileExists(Nssm) then
  begin
    Exec(Nssm, 'stop AtlasBackend',   '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec(Nssm, 'remove AtlasBackend confirm', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec(Nssm, 'stop AtlasBridge',    '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec(Nssm, 'remove AtlasBridge confirm',  '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end
  else
  begin
    Exec('sc.exe', 'delete AtlasBackend', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('sc.exe', 'delete AtlasBridge',  '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;

  // 3) Kill any bundled python.exe still holding files in {app}\python so the
  //    embedded runtime and site-packages can be replaced. We target ONLY the
  //    Atlas-bundled interpreter path, never the user's system Python.
  if DirExists(ExpandConstant('{app}\python')) then
    Exec('taskkill.exe',
         '/F /FI "IMAGENAME eq python.exe" /FI "MODULES eq ' + ExpandConstant('{app}\python\python311.dll') + '"',
         '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  // Give the OS a moment to release file handles.
  Sleep(1500);
end;

function InitializeSetup(): Boolean;
begin
  // MetaTrader 5 credentials are collected on a wizard page (see
  // InitializeWizard) and written to the .env files before the services
  // start, so Atlas connects to MT5 right after installation. Leaving the
  // fields blank keeps the old behaviour (configure later from the dashboard).
  Result := True;
end;

// Called right before files are installed (after the user clicks Install and
// before [InstallDelete]/[Files]). Perfect place to release file locks.
function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  StopAtlasServices();
  Result := '';  // empty = proceed
end;
