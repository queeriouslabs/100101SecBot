# 100101SecBot
A security bot to guard your secret rebel hideout.

# Starting, restarting, and stopping
Front door access is managed with 3 services, one for the RFID reader, an authorizer, and one to open the latch.

Note: see https://www.youtube.com/watch?v=y8OnoxKotPQ

The services are managed with systemd.  The driving service is the `front_door_latch.service`.

```bash
$ sudo systemctl start front_door_latch.service
$ sudo systemctl restart front_door_latch.service
$ sudo systemctl stop front_door_latch.service
```

The other services are `front_door_rfid_reader.service` and `front_door_authorizer.service`.  They are bound to the `front_door_latch.service` and stop/restart/start as a group.

# File Locations
## Logs
Logging is in `/var/log/queeriouslabs/acl.log`

## Access Control Data
required data for access control is in the `data` directory.

## Adding and removing users from Access Control
Adding and removing users is managed via edited the `rfids.csv` file in the `data` directory.  An interface will be built, but for now, add/remove/modify
rows in the csv file.

# Troubleshooting
Check the logs
Restart the services

```bash
$ sudo systemctl restart front_door_latch.service
```

If that doesn't work, check dmesg for errors related to USB devices

```bash
$ sudo dmesg -xT
```

# Updates
Do not update on the pi.  Update on a local repo, run pytest to ensure no test failures, and create a PR.  Ping matt.
