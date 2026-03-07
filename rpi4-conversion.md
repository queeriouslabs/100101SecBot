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


