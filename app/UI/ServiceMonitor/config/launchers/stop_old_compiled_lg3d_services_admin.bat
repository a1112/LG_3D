@echo off
setlocal
for %%P in (
    CapTure.exe
    Cap2d.exe
    writePLC.exe
    二级.exe
    ApiServer.exe
    AlgServer.exe
    Alg2DServer.exe
) do (
    taskkill /F /T /IM "%%P"
)
