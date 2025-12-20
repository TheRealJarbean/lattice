# Lattice
---
Lattice is a visual device control and monitoring tool for use with hardware commonly used in molecular beam epitaxy (MBE) systems.

## Downloads
Releases are hosted on [GitHub](https://github.com/TheRealJarbean/lattice/releases). Linux users should build from source.

## Building From Source
The following tools are required:

- git
- [uv](https://docs.astral.sh/uv/)
- python >=3.13

After installing the required tools, follow these instructions:

1. Clone the repository
`git clone https://github.com/TheRealJarbean/lattice.git`

2. Open the project in your preferred IDE (ex VSCode) or cd into the folder
`cd lattice`

3. Create a virtual environment
`uv venv`

3. Activate the virtual environment using the command provided after creation

4. Install project dependencies
`uv sync`

5. Build with pyinstaller
`pyinstaller ./src/lattice/app.py`

# Misc Notes

## Using PySide6 development tools
- /.venv/Scripts contains many helpful scripts used in designing/updating this software (primarily pyside6-designer)
- https://www.pythonguis.com/tutorials/pyside6-embed-pyqtgraph-custom-widgets/

## How to use logger:
- In the top level (app) file the logger is configured
- In every other module, logger is imported and set to logging.getLogger(__name__) (__name__ automatically names the logger after the file it is in, allowing for easy tracing)
- logger.debug(statement) allows printing of debug statements only in debug mode across entire application
- LOG_LEVEL env variable must be set to "DEBUG" for debug messages to print
- Debug mode PowerShell example: run application with "$env:LOG_LEVEL = "DEBUG"; python .\src\lattice\app.py"

## Replacing PySide6
This application uses PySide6 for Qt for Python bindings, which is licensed under LGPL v3. If you would like to replace it, follow these instructions:
1. Install your preferred bindings library
2. Replace all "from PySide6" import statements
3. Rebuild the application (if using bundled release)