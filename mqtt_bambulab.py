import json
import ssl
import traceback
from threading import Thread

import paho.mqtt.client as mqtt

from config import PRINTER_ID, PRINTER_CODE, PRINTER_IP
from messages import GET_VERSION, PUSH_ALL
from spoolman_client import fetchSpoolList, patchExtraTags


def num2letter(num):
  return chr(ord("A") + int(num))


def publish(client, msg):
  result = client.publish(f"device/{PRINTER_ID}/request", json.dumps(msg))
  status = result[0]
  if status == 0:
    print(f"Sent {msg} to topic device/{PRINTER_ID}/request")
    return True

  print(f"Failed to send message to topic device/{PRINTER_ID}/request")
  return False


# Inspired by https://github.com/Donkie/Spoolman/issues/217#issuecomment-2303022970
def on_message(client, userdata, msg):
  global LAST_AMS_CONFIG
  # TODO: Consume spool
  try:
    data = json.loads(msg.payload.decode())
    print(data)
    if "print" in data and "vt_tray" in data["print"]:
      print(data)
      LAST_AMS_CONFIG["vt_tray"] = data["print"]["vt_tray"]

    if "print" in data and "ams" in data["print"] and "ams" in data["print"]["ams"]:
      print(data)
      LAST_AMS_CONFIG["ams"] = data["print"]["ams"]["ams"]

      print(LAST_AMS_CONFIG)
      for ams in data["print"]["ams"]["ams"]:
        print(f"AMS [{num2letter(ams['id'])}] (hum: {ams['humidity']}, temp: {ams['temp']}ºC)")
        for tray in ams["tray"]:
          if "tray_sub_brands" in tray:
            print(
                f"    - [{num2letter(ams['id'])}{tray['id']}] {tray['tray_sub_brands']} {tray['tray_color']} ({str(tray['remain']).zfill(3)}%) [[ {tray['tag_uid']} ]]")

            found = False
            for spool in SPOOLS:
              if not spool.get("extra", {}).get("tag"):
                continue
              tag = json.loads(spool["extra"]["tag"])
              if tag != tray["tag_uid"]:
                continue

              found = True

              setActiveTray(spool['id'], spool["extra"], ams['id'], tray["id"])

              # TODO: filament remaining - Doesn't work for AMS Lite
              # requests.patch(f"http://{SPOOLMAN_IP}:7912/api/v1/spool/{spool['id']}", json={
              #  "remaining_weight": tray["remain"] / 100 * tray["tray_weight"]
              # })

            if not found:
              print("      - Not found. Update spool tag!")
  except Exception as e:
    traceback.print_exc()


def on_connect(client, userdata, flags, rc):
  print("Connected with result code " + str(rc))
  client.subscribe(f"device/{PRINTER_ID}/report")
  publish(client, GET_VERSION)
  publish(client, PUSH_ALL)


def setActiveTray(spool_id, spool_extra, ams_id, tray_id):
  patchExtraTags(spool_id, spool_extra, {
    "active_tray": json.dumps(f"{PRINTER_ID}_{ams_id}_{tray_id}"),
  })

  # Remove active tray from inactive spools
  for old_spool in SPOOLS:
    if spool_id != old_spool["id"] and old_spool["extra"]["active_tray"] == json.dumps(
        f"{PRINTER_ID}_{ams_id}_{tray_id}"):
      patchExtraTags(old_spool["id"], old_spool["extra"], {"active_tray": json.dumps("")})


# Fetch spools from spoolman
def fetchSpools():
  global SPOOLS
  SPOOLS = fetchSpoolList()
  return SPOOLS


def async_subscribe():
  global MQTT_CLIENT
  MQTT_CLIENT = mqtt.Client()
  MQTT_CLIENT.username_pw_set("bblp", PRINTER_CODE)
  ssl_ctx = ssl.create_default_context()
  ssl_ctx.check_hostname = False
  ssl_ctx.verify_mode = ssl.CERT_NONE
  MQTT_CLIENT.tls_set_context(ssl_ctx)
  MQTT_CLIENT.tls_insecure_set(True)
  MQTT_CLIENT.on_connect = on_connect
  MQTT_CLIENT.on_message = on_message
  MQTT_CLIENT.connect(PRINTER_IP, 8883)
  MQTT_CLIENT.loop_forever()


# Start the asynchronous processing in a separate thread
thread = Thread(target=async_subscribe)
thread.start()


def getLastAMSConfig():
  global LAST_AMS_CONFIG
  return LAST_AMS_CONFIG


def getMqttClient():
  global MQTT_CLIENT
  return MQTT_CLIENT


MQTT_CLIENT = {}  # Global variable storing MQTT Client
LAST_AMS_CONFIG = {}  # Global variable storing last AMS configuration
SPOOLS = fetchSpools()  # Global variable storing latest spool from spoolman
