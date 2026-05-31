' Hermes Desktop - double-click to launch
' Opens a native desktop window, not a browser
Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

strPath = fso.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strPath

PYTHON = "..\hermes-agent\venv\Scripts\python.exe"
If Not fso.FileExists(PYTHON) Then
    MsgBox "Python not found: " & vbCrLf & strPath & "\" & PYTHON, 48, "Hermes Desktop"
    WScript.Quit 1
End If

' Start server - will open its own native desktop window
WshShell.Run """" & PYTHON & """ -u server.py", 0, False
