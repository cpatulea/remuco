#!/usr/bin/python
import os
from win32com.shell import shell, shellcon

xdg_config_home = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
xdg_cache_home = shell.SHGetFolderPath(0, shellcon.CSIDL_LOCAL_APPDATA, 0, 0)
