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
     "StartupFolder",          # Directory_
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

#includefiles = ['locales/','locales/ru_RU','locales/ru_RU/LC_MESSAGES','locales/en_US', ,'locales/ru_RU/LC_MESSAGES/default.mo', 'locales/en_US/LC_MESSAGES/default.mo', 'settings.cfg']
includefiles = ['locales/','settings.cfg']

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
    version = "1.1",
    description = "Serial flow monitor",
    author = "MakeItLab",
    author_email = "hackspace@makeitlab.ru",
    options = options,
    executables = executables,
)
