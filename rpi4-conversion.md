# Power

the rpi4 uses a USB-C for power in, so the old AC/DC converter was swapped out to one with a USB-C cable.

# Doorbell Audio not working
Audio is required to run the doorbell.  The rpi4 was not finding and audio device on initialization. e.g. `raspi-config > System Options > S2 Audio` reported "No internal audio devices found"

I could not run alsamixer as a user.

As root, it did run, but showed the wrong card:
vc4-hdmi-0

What i want is the `bcm2835 Headphones` and I want that as the default card selected by alsa.

```
$ cat /proc/asound/cards
 0 [vc4hdmi0       ]: vc4-hdmi - vc4-hdmi-0
                      vc4-hdmi-0
 1 [vc4hdmi1       ]: vc4-hdmi - vc4-hdmi-1
                      vc4-hdmi-1
 2 [Headphones     ]: bcm2835_headpho - bcm2835 Headphones
                      bcm2835 Headphones
```

https://www.alsa-project.org/main/index.php/Setting_the_default_device


Now root selected the right card when running alsamixer.
`sudo aplay <something>.wav` worked.

Running as a user was resolved by adding myself to the `audio` group.

# Doorbell runs in a venv
I created a python virtualenv in /opt/venv to segregate the requirements for the doorbrell.  As python marches on, it's harder and harder to install into the system python distribution, especially as the system packages are not really managed well at the distribution level.

The systemd unit file was updated to use this venv for it's python interpretter.


# Piplate not recognized
I replaced this with a relay, which requires changing the code to remove piplates and include acuating the relay via a GPIO.

The relay trigger is connected to pin GPIO23 and is modelled as a gpiozero.LED(23).

```
relay = gpiozero.LED(23)
relay.on()
relay.off()
```

This also required updating the tests as the relay was an important test fixture


# Doorbell grabbing wrong input
The doorbell is a USB device which presents as a keyboard and mouse.  The python script which translates a key-press to audio uses the evdev library to list devices in `/dev/input` and selects one by finding the string "Key-1" in the name.

```python
<insert doorbell.py code>
```

As the doorbell presents two devices, however, this is not sufficient.  
```
/dev/input $ ls -ltra by-id/
total 0
lrwxrwxrwx 1 root root   9 Mar 12 13:14 usb-Key-1_FD-KYMS_FD-KYMU-if01-mouse -> ../mouse0
lrwxrwxrwx 1 root root   9 Mar 12 13:14 usb-0000_USB_OPTICAL_MOUSE-mouse -> ../mouse1
lrwxrwxrwx 1 root root   9 Mar 12 13:14 usb-0000_USB_OPTICAL_MOUSE-event-mouse -> ../event3
lrwxrwxrwx 1 root root   9 Mar 12 13:14 usb-Key-1_FD-KYMS_FD-KYMU-event-kbd -> ../event1
lrwxrwxrwx 1 root root   9 Mar 12 13:14 usb-Key-1_FD-KYMS_FD-KYMU-if01-event-mouse -> ../event0
lrwxrwxrwx 1 root root   9 Mar 12 13:14 usb-413d_2107-event-kbd -> ../event2
```

It's unclear if presenting as two devices is new behavior.  Redgardless, the mouse device is presenting before the keboard device, which fulfils the name criteria, but the mouse device does not send events when the button is pressed.

Unfortunately evdev does not have any disambiguating information available, so a work-around to check the above mapping in /dev/input/by-id is used to select the right input device


# Doorbell not playing audio (Again)

The rpi reorderd the cards and now the correct card (Headphones) as a different number.

/etc/asound.conf was updated to

```
defaults.pcm.!card Headphones
defaults.ctl.!card Headphones
```
https://superuser.com/questions/626606/how-to-make-alsa-pick-a-preferred-sound-device-automatically

## Doorbell failing after one ring

`simpleaudio` is segfaulting after playing the sound.

The systemd unit file was not configured to restart.

```bash
$ source /opt/venv/bin/activate
(venv) pi@the-gibson:~/Projects/large-doorbell-button $ python
```

```python
Python 3.13.5 (main, Jun 25 2025, 18:55:22) [GCC 14.2.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> import simpleaudio
>>> fname = "voy_door_chime.wav"
>>> fname
'voy_door_chime.wav'
>>> wo = simpleaudio.WaveObject.from_wave_file(fname)
>>> po = wo.play()
>>> Segmentation fault
```

This is causing the doorbell to segfault, and it doesn't restart after.

systemd unit file:
```
[Unit]
Description=Front Doorbell

[Service]
WorkingDirectory=/home/pi/Projects/large-doorbell-button/
User=pi
Type=simple
ExecStart=/opt/venv/bin/python3 /home/pi/Projects/large-doorbell-button/doorbell.py

[Install]
WantedBy=multi-user.target
```

config to restart was added to the systemd unit file which papers over the segfault, as the service restarts after the segfault.

```
[Unit]
Description=Front Doorbell

[Service]
WorkingDirectory=/home/pi/Projects/large-doorbell-button/
User=pi
Type=simple
ExecStart=/opt/venv/bin/python3 /home/pi/Projects/large-doorbell-button/doorbell.py
Restart=always
RestartSec=1s

[Install]
WantedBy=multi-user.target
```

# Home directory file ownership was wrong

https://serverfault.com/a/445504

just run
```
$ sudo chown <user>:<user> -R . 
```

in your home directory where `<user>` is your user name
