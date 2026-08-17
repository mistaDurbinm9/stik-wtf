' Launches the power agent with no console window at all.
' A scheduled task calling powershell.exe directly flashes a console every run, even with
' -WindowStyle Hidden — the window exists before PowerShell can hide it. wscript.exe has
' no console of its own, and Run(..., 0, False) starts the child hidden.
Dim shell, here
Set shell = CreateObject("WScript.Shell")
here = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
shell.Run "powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File """ & here & "stik-power-pc.ps1""", 0, False
