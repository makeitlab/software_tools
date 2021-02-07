import sys
from cx_Freeze import setup, Executable

product_name = 'SFMonitor'

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

shortcut_table = [
    ("DesktopShortcut",        # Shortcut
     "DesktopFolder",         # Directory_
     "SFMonitor",              # Name
     "TARGETDIR",              # Component_
     "[TARGETDIR]sfmonitor.exe",# Target
     None,                     # Arguments
     None,                     # Description
     None,                     # Hotkey
     None,                     # Icon
     None,                     # IconIndex
     None,                     # ShowCmd
     'TARGETDIR'               # WkDir
     ),

    ("StartupShortcut",        # Shortcut
     "StartMenuFolder",        # Directory_
     "SFMonitor",              # Name
     "TARGETDIR",              # Component_
     "[TARGETDIR]sfmonitor.exe",   # Target
     None,                     # Arguments
     None,                     # Description
     None,                     # Hotkey
     None,                     # Icon
     None,                     # IconIndex
     None,                     # ShowCmd
     'TARGETDIR'               # WkDir
     ),
]

msi_data = {"Shortcut": shortcut_table}

msi_options = {
    'upgrade_code': '{9f77e33d-48f7-cf34-33e9-efcfd80eed10}',
    'add_to_path': False,
    'initial_target_dir': r'[ProgramFilesFolder]\%s' % product_name,
    'data':msi_data
}

includefiles = ['SerialFlow/','locales/','settings.cfg','plot.ico']

options = {
    'build_exe': {
        'includes': 'atexit',
	'include_files':includefiles
    },
    'bdist_msi': msi_options,
}

executables = [
    Executable('sfmonitor.pyw', base=base, icon='plot.ico')
]

setup(
    name = "SFMonitor",
    version = "1.2",
    description = "Serial flow monitor",
    author = "MakeItLab",
    author_email = "hackspace@makeitlab.ru",
    options = options,
    executables = executables,
)
