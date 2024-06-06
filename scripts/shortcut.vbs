Set Shell = CreateObject("WScript.Shell")
Set Link = Shell.CreateShortcut(WScript.Arguments(0))
Link.TargetPath = "%windir%\system32\cmd.exe /c start """" ""%CD%\bin\MeasureSummary.exe"""
Link.WorkingDirectory = ""
Link.IconLocation = WScript.Arguments(1)
Link.WindowStyle = 3
Link.Save
