from config import PRINTER_ID
import json

from spoolman_client import consumeSpool, patchExtraTags, fetchSpoolList

def trayUid(ams_id, tray_id):
  return f"{PRINTER_ID}_{ams_id}_{tray_id}"

def augmentTrayDataWithSpoolMan(spool_list, tray_data, tray_id):
  tray_data["matched"] = False
  for spool in spool_list:
    if spool.get("extra") and spool["extra"].get("active_tray") and spool["extra"]["active_tray"] == json.dumps(tray_id):
      #TODO: check for mismatch
      tray_data["remaining_weight"] = spool["remaining_weight"]
      tray_data["matched"] = True
      break

  if tray_data.get("tray_type") and tray_data["tray_type"] != "" and tray_data["matched"] == False:
    tray_data["issue"] = True
  else:
    tray_data["issue"] = False

def spendFilaments(filaments_usage):
  print(filaments_usage)
  ams_usage = {}
  for tray_id, usage in filaments_usage:
    if tray_id != -1:
      #TODO: hardcoded ams_id
      if ams_usage.get(trayUid(0, tray_id)):
        ams_usage[trayUid(0, tray_id)] += float(usage)
      else:
        ams_usage[trayUid(0, tray_id)] = float(usage)

  for spool in fetchSpools():
    #TODO: What if there is a mismatch between AMS and SpoolMan?
    if spool.get("extra") and spool.get("extra").get("active_tray") and ams_usage.get(json.loads(spool.get("extra").get("active_tray"))):
      consumeSpool(spool["id"], ams_usage.get(json.loads(spool.get("extra").get("active_tray"))))

def setActiveTray(spool_id, spool_extra, ams_id, tray_id):
  if spool_extra == None:
    spool_extra = {}

  if not spool_extra.get("active_tray") or json.loads(spool_extra.get("active_tray")) != trayUid(ams_id, tray_id):
    patchExtraTags(spool_id, spool_extra, {
      "active_tray": json.dumps(trayUid(ams_id, tray_id)),
    })

    # Remove active tray from inactive spools
    for old_spool in fetchSpools(cached=True):
      if spool_id != old_spool["id"] and old_spool.get("extra") and old_spool["extra"].get("active_tray") and json.loads(old_spool["extra"]["active_tray"]) == trayUid(ams_id, tray_id):
        patchExtraTags(old_spool["id"], old_spool["extra"], {"active_tray": json.dumps("")})
  else:
    print("Skipping set active tray")

# Fetch spools from spoolman
def fetchSpools(cached=False):
  global SPOOLS
  if not cached:
    SPOOLS = fetchSpoolList()
  return SPOOLS

SPOOLS = fetchSpools()  # Global variable storing latest spool from spoolman
