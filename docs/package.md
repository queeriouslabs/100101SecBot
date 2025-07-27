# Secbot

## Directories
- bin/ - Runnable script to be put on PATH
- data/ - csv files for rfids and hours
- examples/ - illustrative examples of creating secbot comms based services
- scripts/ - utility scripts
- secbot/ - python module for the core secbot functionality
- services/ - services built up using secbot core functionality that are in use as infrastructure
- systemd/ - systemd scripts for the services
- tests/ - pytest based tests which ought to always pass

## Installation
Clone the repo

Create a virtualenv 
```bash
$ python3 -m venv venv
```

Activate the env
```bash
$ . venv/bin/activate
````

Install the requirements
```bash
$ pip install -r requirements.txt
```

Link the systemd scripts
```bash
$ sudo ln -s ./systemd/broadcast.service /etc/systemd/system/broadcast.service
$ sudo ln -s ./systemd/front_door_authorizer.service /etc/systemd/system/front_door_authorizer.service
$ sudo ln -s ./systemd/front_door_latch.service /etc/systemd/system/front_door_latch.service
$ sudo ln -s ./systemd/front_door_rfid_reader.service /etc/systemd/system/front_door_rfid_reader.service
$ sudo ln -s ./systemd/scheduled-reboot.service /etc/systemd/system/scheduled-reboot.service
$ sudo ln -s ./systemd/scheduled-reboot.timer /etc/systemd/system/scheduled-reboot.timer
```

Reload systemd
```bash
$ sudo systemctl daemon-reload
```

Enable the new services:
```bash
$ sudo systemctl enable broadcast.service
$ sudo systemctl enable front_door_authorizer.service
$ sudo systemctl enable front_door_latch.service
$ sudo systemctl enable front_door_rfid_reader.service
$ sudo systemctl enable scheduled-reboot.service
$ sudo systemctl enable scheduled-reboot.timer
```

Start the front door and broadcast services
```bash
$ sudo systemctl start broadcast.service
$ sudo systemctl start front_door_latch.service
$ sudo systemctl start front_door_authorizer.service
$ sudo systemctl start front_door_rfid_reader.service
```

Link the `bin/secbot` bash script into `/usr/bin/`
```bash
$ sudo ln -s bin/secbot /usr/bin/secbot
```


