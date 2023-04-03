# Greencube controller

## Install

Either install the dependencies with the package manager, pip or venv.

Create venv with required packages:
``` commandline
python3 -m venv venv
source ./venv/bin/activate
pip3 install -e .
```

## Useage

If you chose the venv, make sure it's activated before running the program.
Venv is active when the prompt begins with `(venv)`

Activate with:
`source ./venv/bin/activate`<br>
Deactivate with: `deactivate`

````commandline
usage: greencube_control.py [-h] -l LOCATOR [-e ELEVATION] [-z HORIZON]
                            [-f FREQ] [-t TUNESTEP] [-d] [-n NORAD]
                            [-r RIGHOST] [-p RIGPORT] [-R ROTHOST]
                            [-P ROTPORT] [-T THRESHOLD] [-v]

Control radio doppler for greencube

options:
  -h, --help            show this help message and exit
  -l LOCATOR, --locator LOCATOR
                        Your maidenhead locator
  -e ELEVATION, --elevation ELEVATION
                        Your elevation
  -z HORIZON, --horizon HORIZON
                        Above this horizon to track rotator
  -f FREQ, --freq FREQ  Frequency to track
  -t TUNESTEP, --tunestep TUNESTEP
                        TX tuning step
  -d, --disable_tune    Disable VFO tuning on radio
  -n NORAD, --norad NORAD
                        NORAD ID to track
  -r RIGHOST, --righost RIGHOST
                        rigctld host
  -p RIGPORT, --rigport RIGPORT
                        rigctl port
  -R ROTHOST, --rothost ROTHOST
                        rotctld host
  -P ROTPORT, --rotport ROTPORT
                        rotctl port
  -T THRESHOLD, --threshold THRESHOLD
                        rotctl move threshold
  -v, --verbosity       Increase verbosity
````