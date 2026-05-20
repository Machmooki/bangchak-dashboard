# Dashboard Bangchak

Recommended root folder:

- `excel/` - keep the dashboard Excel file here
- `system/` - FastAPI app, static web UI, tests, and build scripts
- `Run Dashboard.bat` - Windows launcher
- `Run Dashboard.command` - macOS launcher
- `Build Portable.bat` - build a Windows portable package
- `Run Portable Dashboard.bat` - run the already-built portable package

## Run On Windows

Double-click:

```text
Run Dashboard.bat
```

The launcher starts the local FastAPI server and opens the browser automatically.

## Run On macOS

Double-click:

```text
Run Dashboard.command
```

macOS needs Python 3 installed. The app still reads the same Excel file from `excel/`.

## Excel Source

The dashboard reads:

```text
excel\00_Prospecting assign lot1_as of 17 Apr.xlsx
```

Current dashboard data comes from:

- `Summary`
- `Sheet7`

## Portable Build

For a Windows machine without Python, build the portable package first:

```text
Build Portable.bat
```

Output:

```text
system\dist\Dashboard Bangchak\
```
