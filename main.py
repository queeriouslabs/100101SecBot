#!/usr/bin/python3 -u
import evdev
import datetime
import queue
import threading
import time
import yaml


def date_now():
  return datetime.datetime.fromtimestamp(time.time())

while True:
    try:
        import piplates.RELAYplate as RELAY
        break
    except FileNotFoundError as e:
        time.sleep(0.1)


print("NOTICE! All logging is now being done to an external file for persistence.")

def log(msg):
  with open("/home/r/notsecbot/top_secret_logs.txt", "a") as f:
    f.write(time.strftime("%Y-%m-%d %H:%M:%S (%a, %b %m, %Y at %I:%M:%S %p)") + ": " + msg + "\n")

#### Relay Thread

class RelayThread(threading.Thread):

  def relay_open(self, t=3.0):
    # See https://pi-plates.com/relayplate-users-guide/ for basics on the relay plate and library
    # There's only one relay plate and the first relay is broken, so we're using the second
    log(f"T: Opening for some seconds {t}")
    failed = True
    for i in range(5):
      try:
        RELAY.relayON(0, 2)
        failed = False
        break
      except AssertionError:
        log(f"Relay is missing, sleeping for a moment")
        time.sleep(0.1)
    if failed:
      log(f"Relay missing for too long. Exiting relay thread.")
      exit()
    time.sleep(t)
    RELAY.relayOFF(0, 2)
    log(f"T: Closed")

  def run(self):
    log(f"T: running")
    running = True
    while running:
      task = self.q.get()
      log(f"T: Got task {task}")
      if type(task) != float:
        running = False
      else:
        open_time = task - time.time()
        if open_time > 0.0:
          self.relay_open(open_time)
      self.q.task_done()


relay_thread = RelayThread()
relay_thread.start()
relay_thread.q = queue.Queue()

def open_relay(t):
  relay_thread.q.put(time.time() + t)

def shutdown_relay():
  relay_thread.q.put(None)
  relay_thread.join()

####/Relay Thread

#### RFID Reader Stuff

rfid_reader_name = "Barcode Reader "
# rfid_reader_name = "HID 413d:2107"
devices = [evdev.InputDevice(path) for path in evdev.list_devices()]
rfid_reader = [d for d in devices if d.name == rfid_reader_name][0]

for d in devices:
  if d != rfid_reader:
    d.close()

log(f"{rfid_reader}")

def read_id_emit():
  keys = []
  for ev in rfid_reader.read_loop():
    if ev.type != evdev.ecodes.EV_KEY:
      continue
    c = evdev.categorize(ev)
    if c.keystate != 0:
      continue
    if ev.code == evdev.ecodes.KEY_ENTER:
      yield "".join(map(str, keys))
      keys = []
    else:
      log(f"Appending keycode: {c.keycode}, {c.keycode[4:]}")
      try:
        keys.append(int(c.keycode[4:]))
      except ValueError:
        pass

####/RFID Reader Stuff

def on_close():
  global rfid_reader
  rfid_reader.close()
  shutdown_relay()

#### Fetch IDs

class IDs:
  def __init__(self, yaml):
    self.yaml = yaml
    if type(yaml) != dict:
      raise ValueError("Expected YAML top-level to be a dict / map, not %s" % type(yaml))
    if set(self.yaml.keys()) != set(["levels", "rfids"]):
      raise ValueError("Unexpected top level keys")
  def check_level(self, level):
    hour = date_now().hour # .today()?
    if level in self.yaml["levels"]:
      level = self.yaml["levels"][level]
      if hour in range(*level["hours"]):
        return True
      else:
        log(f"Level found - hours wrong")
    else:
      log(f"Level not found")
    return False
  def check_access(self, id):
    for (issuer, rfids) in self.yaml["rfids"].items():
      for rfid in rfids:
        #log("Comparing '%s' with '%s'" % (str(rfid["id"]).rjust(10, "0"), id))
        if rfid["id"] == id:
          if self.check_level(rfid["level"]):
            return True
          else:
            log(f"Correct RFID but level check failed")
    return False

def get_ids():
  o = None
  with open("ids.yaml", "r") as f:
    o = yaml.safe_load(f.read())
  return IDs(o)

####/Fetch IDs

#### Main Loop

try:
  for id in read_id_emit():
    log(f"Read id {id}")
    ids = get_ids()
    if ids.check_access(id):
      log(f"Access granted; opening!")
      open_relay(3.5)
    else:
      log(f"Unknown or out of range ID; access denied.")
    if not relay_thread.is_alive():
      log(f"Relay thread died, exiting")
      rfid_reader.close()
      exit()
except KeyboardInterrupt:
  log(f"Exiting")
  on_close()

####/Main Loop
