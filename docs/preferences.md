# Configuration

## Preferences

Preferences can be edited by clicking the **preferences** button on the menu bar.

| Name | Default | Description |
| ---- | ------- | ----------- |
| **Pressure Email Warning Threshold** | **1e-5** | When this pressure is exceeded, an email alert is sent. |
| **Display Time as Local Time** | **True** | For use in plots. False displays time relative to application start time. |

## Parameters

### Source Safety Settings

Can be changed by clicking the **Safety** button of a source in the **Sources tab**. The safe **rate limit** will be applied automatically when the process variable falls between the **From** and **To** values. The **max setpoint** is the maximum value users are allowed to type in the setpoint box on the **Source tab** and the maximum value allowed for the **Wait Until Setpoint** recipe action. **Stability tolerance** is the maximum distance (in either direction) that the process variable can be from the setpoint to be considered "stable".

!!! warning "Warning"
    Source safety settings are a Lattice feature, and are ***NOT*** stored on the source controller. If Lattice is closed, safety settings will ***NOT*** be applied to the source!

### Source PID Settings
Can be changed by clicking the **PID** button of a source in the **Sources tab**. The PID values seen when opening the settings modal are a reflection of the values stored on the source; and changed values are applied instantaneously and are *not* stored internally. Any changes to the PID values of a source (such as via a front panel or autotune) will *not* be overridden by Lattice.

## Email Alerts

### Setup
Email alerts can be configured under the **Email Alerts** tab in the **Preferences** menu while Lattice is open. Once a sender and recipients have been added, email alerts will automatically be sent from the sender to the recipients with a descriptive message when any of the below conditions occur.

### Conditions
Email alerts will be sent under the following conditions:
- Pressure of any pressure gauge exceeds **Pressure Email Warning Threshold** specified in Preferences.

!!! info "Alert Frequency"
    Alerts have an enforced interval of 15 minutes between alerts in order to prevent the sending email account from being flagged as spam.

## Theme

**Pressure gauge colors** are set automatically by HSV separation based on the number of pressure gauges. 

**Source colors** can be changed by clicking the circle next to their name in the **Sources tab**. This changes the color of both their **Process Variable line** and **dashed Working Setpoint line** in the plot.

## Hardware

Use the included **Configurator** tool to add and remove hardware devices.