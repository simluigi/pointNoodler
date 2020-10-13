@echo off
		set GIT_INSTALL_ROOT=%USERPROFILE%\scoop\apps\git\current
		set VIM=%USERPROFILE%\scoop\apps\vim\current
		set PATH=%PATH%;%USERPROFILE%\scoop\apps\python27\current\Scripts;%USERPROFILE%\scoop\shims
		start pageant D:/.ssh/id_rsa.ppk
		set GIT_SSH=%USERPROFILE%\scoop\shims\plink.exe
		start