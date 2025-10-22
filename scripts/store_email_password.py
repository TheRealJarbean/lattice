"""
A simple script to store password for email account in local OS keyring.

Author: Jaron Anderson
Data: 10-22-2025
Version: 1.0

# DESCRIPTION
The password that is stored is a Google account **app password**. The **app password** is generated once by logging in
to the account as normal, and navigating to the settings page linked below.

# NOTES
    - DO NOT SAVE OR COMMIT THE APP PASSWORD. Enter it, run the script, and then undo changes to the file.

# LINKS
Manage App Passwords - https://myaccount.google.com/apppasswords
"""

import keyring

password = '' # Enter password, DO NOT SAVE, run, and undo
keyring.set_password('mbe_software', 'mbe.lab.alerts@gmail.com', password)