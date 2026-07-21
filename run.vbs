' Launch Pokemon Save Sync with no console window at all.
' Double-click this file to run the app silently.
Set fso = CreateObject("Scripting.FileSystemObject")
Set sh = CreateObject("WScript.Shell")

' Run from the folder this script lives in
sh.CurrentDirectory = fso.GetParentFolderName(WScript.ScriptFullName)

' 0 = hidden window, False = don't wait for it to finish
sh.Run "uvw run pythonw main.py", 0, False
