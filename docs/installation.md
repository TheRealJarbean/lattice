# Installation

## Downloads
Releases are hosted on [GitHub](https://github.com/TheRealJarbean/lattice/releases). Linux users should build from source.

## Building From Source
The following tools are required:

- git
- [uv](https://docs.astral.sh/uv/)
- python >=3.13

After installing the required tools, follow these instructions:
```bash
# 1. Clone the repository
git clone https://github.com/TheRealJarbean/lattice.git

# 2. Open the project in your preferred IDE with a terminal (ex VSCode) or cd into the folder
cd lattice

# 3. Create a virtual environment
uv venv

# 4. IMPORTANT: Activate the virtual environment using the command provided after creation

# 5. Install project dependencies
uv sync

# 5. Build with pyinstaller
pyinstaller ./src/lattice/app.py
```