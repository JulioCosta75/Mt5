; ===========================================================================
;  Atlas — MT5 Supervisor — Inno Setup script
;  Output:  Atlas_Setup.exe   (single-file installer for Windows VPS)
;  Build:   Run build.bat (downloads payload deps + invokes ISCC.exe)
; ===========================================================================
#define MyAppName      "Atlas"
#define MyAppVersion   "0.2.0"
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

; -- Setup wizard (PyInstaller-built .exe) -------------------------------
Source: "payload\wizard\Atlas Wizard.exe"; DestDir: "{app}";          Flags: ignoreversion

; -- Service & operation scripts -----------------------------------------
Source: "scripts\install_services.bat";    DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\uninstall_services.bat";  DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\start_atlas.bat";         DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\stop_atlas.bat";          DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\open_dashboard.bat";      DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\healthcheck.bat";         DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\bootstrap_pip.bat";       DestDir: "{app}\scripts"; Flags: ignoreversion
Source: "scripts\install_deps.bat";        DestDir: "{app}\scripts"; Flags: ignoreversion

; -- Icons & misc ----------------------------------------------------------
Source: "icons\atlas.ico";  DestDir: "{app}\icons";  Flags: ignoreversion
Source: "LICENSE.txt";      DestDir: "{app}";        Flags: ignoreversion
Source: "README_INSTALL.txt"; DestDir: "{app}";      Flags: ignoreversion

[Dirs]
Name: "{app}\data";  Permissions: users-modify
Name: "{app}\logs";  Permissions: users-modify

[Icons]
Name: "{group}\Atlas Dashboard";    Filename: "{app}\scripts\open_dashboard.bat"; IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Atlas Wizard";       Filename: "{app}\{#MyAppExeName}";            IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Atlas Health Check"; Filename: "{app}\scripts\healthcheck.bat";    IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Stop Atlas";         Filename: "{app}\scripts\stop_atlas.bat";     IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Start Atlas";        Filename: "{app}\scripts\start_atlas.bat";    IconFilename: "{app}\icons\atlas.ico"; Tasks: startmenu
Name: "{group}\Uninstall Atlas";    Filename: "{uninstallexe}"; Tasks: startmenu
Name: "{commondesktop}\Atlas Dashboard"; Filename: "{app}\scripts\open_dashboard.bat"; IconFilename: "{app}\icons\atlas.ico"; Tasks: desktopicon

[Run]
; 1) Install pip into embedded Python and pip-install backend + bridge deps
Filename: "{app}\scripts\bootstrap_pip.bat"; StatusMsg: "Setting up Python runtime..."; Flags: runhidden
Filename: "{app}\scripts\install_deps.bat";  StatusMsg: "Installing Python dependencies (this may take a few minutes)..."; Flags: runhidden

; 2) Install services if user accepted
Filename: "{app}\scripts\install_services.bat"; StatusMsg: "Registering Atlas Windows Services..."; Tasks: installsvc; Flags: runhidden

; 3) Launch the GUI wizard (collects MT5 credentials, writes .env, starts services)
Filename: "{app}\{#MyAppExeName}"; Description: "Run Atlas setup wizard"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{app}\scripts\uninstall_services.bat"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\data"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\python\Lib\site-packages"

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  // Soft warning if MetaTrader5 not detected in common paths.
  if not (FileExists(ExpandConstant('{commonpf}\MetaTrader 5\terminal64.exe')) or
          FileExists(ExpandConstant('{commonpf64}\MetaTrader 5\terminal64.exe')) or
          FileExists(ExpandConstant('{userappdata}\MetaQuotes\Terminal\terminal64.exe'))) then
  begin
    if MsgBox('MetaTrader 5 was not detected on this machine in the usual locations.' #13#10 +
             'Atlas needs MT5 installed and logged in to work.' #13#10 #13#10 +
             'Continue installation anyway?', mbConfirmation, MB_YESNO) = IDNO then
      Result := False;
  end;
end;
