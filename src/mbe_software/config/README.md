# Creating Config Files
If any config files are missing, they will be generated on when the program starts.

# Automatic Config
The following config files are updated automatically in software:
    - theme.yaml
    - parameters.yaml
    - hardware.yaml (through configurator)

Don't edit them manually unless you know what you are doing.

# Manual Config
All other configs can (or must) be edited manually. Make sure you understand the basics of [YAML](https://en.wikipedia.org/wiki/YAML) before editing. YAML is loaded in python as a dictionary, so *don't change the structure* of the file unless you plan to edit code.