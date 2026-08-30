Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

Dim foundPath
foundPath = ""

' Buscar Python portable primero
portablePy = scriptDir & "\python_embed\python.exe"
If fso.FileExists(portablePy) Then
    foundPath = portablePy
End If

' Buscar Python en rutas comunes
If foundPath = "" Then
    Dim paths(4)
    paths(0) = "C:\Python314\python.exe"
    paths(1) = "C:\Python313\python.exe"
    paths(2) = "C:\Python312\python.exe"
    paths(3) = "C:\Python311\python.exe"
    paths(4) = "C:\Python310\python.exe"

    For Each p In paths
        If fso.FileExists(p) Then
            foundPath = p
            Exit For
        End If
    Next
End If

' Buscar en AppData
If foundPath = "" Then
    userName = WshShell.ExpandEnvironmentStrings("%USERNAME%")
    localPaths = Array( _
        "C:\Users\" & userName & "\AppData\Local\Programs\Python\Python314\python.exe", _
        "C:\Users\" & userName & "\AppData\Local\Programs\Python\Python313\python.exe", _
        "C:\Users\" & userName & "\AppData\Local\Programs\Python\Python312\python.exe" _
    )
    For Each p In localPaths
        If fso.FileExists(p) Then
            foundPath = p
            Exit For
        End If
    Next
End If

If foundPath <> "" Then
    WshShell.CurrentDirectory = scriptDir
    WshShell.Run """" & foundPath & """ """ & scriptDir & "\main.py""", 0, False
Else
    MsgBox "Python no encontrado." & vbCrLf & vbCrLf & "Ejecuta Iniciar.bat primero para instalarlo.", 16, "Error"
End If
