import json
import traceback
import uuid

from flask import Flask, request, render_template, redirect, url_for

from config import BASE_URL, AUTO_SPEND
from filament import generate_filament_brand_code, generate_filament_temperatures
from frontend_utils import color_is_dark
from messages import AMS_FILAMENT_SETTING
from mqtt_bambulab import fetchSpools, getLastAMSConfig, publish, getMqttClient, setActiveTray
from spoolman_client import patchExtraTags, getSpoolById
from spoolman_service import augmentTrayDataWithSpoolMan, trayUid

app = Flask(__name__)

@app.route("/spool_info")
def spool_info():
  try:
    tag_id = request.args.get("tag_id")

    last_ams_config = getLastAMSConfig()
    ams_data = last_ams_config.get("ams", [])
    vt_tray_data = last_ams_config.get("vt_tray", {})

    print(ams_data)
    print(vt_tray_data)

    if not tag_id:
      return "TAG ID is required as a query parameter (e.g., ?tagid=RFID123)"

    spools = fetchSpools()
    current_spool = None
    for spool in spools:
      if not spool.get("extra", {}).get("tag"):
        continue
      tag = json.loads(spool["extra"]["tag"])
      if tag != tag_id:
        continue
      current_spool = spool

    # TODO: missing current_spool
    return render_template('spool_info.html', tag_id=tag_id, current_spool=current_spool, ams_data=ams_data, vt_tray_data=vt_tray_data, color_is_dark=color_is_dark, AUTO_SPEND=AUTO_SPEND)
  except Exception as e:
    traceback.print_exc()
    return render_template('error.html', exception=str(e))


@app.route("/tray_load")
def tray_load():
  tag_id = request.args.get("tag_id")
  ams_id = request.args.get("ams")
  tray_id = request.args.get("tray")
  spool_id = request.args.get("spool_id")

  if not all([tag_id, ams_id, tray_id, spool_id]):
    return "Missing RFID, AMS ID, or Tray ID or spool_id."

  try:
    # Update Spoolman with the selected tray
    spool_data = getSpoolById(spool_id)

    setActiveTray(spool_id, spool_data["extra"], ams_id, tray_id)

    ams_message = AMS_FILAMENT_SETTING
    ams_message["print"]["sequence_id"] = 0
    ams_message["print"]["ams_id"] = int(ams_id)
    ams_message["print"]["tray_id"] = int(tray_id)
    ams_message["print"]["tray_color"] = spool_data["filament"]["color_hex"].upper() + "FF"

    if "nozzle_temperature" in spool_data["filament"]["extra"]:
      nozzle_temperature_range = spool_data["filament"]["extra"]["nozzle_temperature"].strip("[]").split(",")
      ams_message["print"]["nozzle_temp_min"] = int(nozzle_temperature_range[0])
      ams_message["print"]["nozzle_temp_max"] = int(nozzle_temperature_range[1])
    else:
      nozzle_temperature_range_obj = generate_filament_temperatures(spool_data["filament"]["material"],
                                                                    spool_data["filament"]["vendor"]["name"])
      ams_message["print"]["nozzle_temp_min"] = int(nozzle_temperature_range_obj["filament_min_temp"])
      ams_message["print"]["nozzle_temp_max"] = int(nozzle_temperature_range_obj["filament_max_temp"])

    ams_message["print"]["tray_type"] = spool_data["filament"]["material"]
    filament_brand_code = generate_filament_brand_code(spool_data["filament"]["material"],
                                                       spool_data["filament"]["vendor"]["name"],
                                                       spool_data["filament"]["extra"].get("type", ""))
    ams_message["print"]["tray_info_idx"] = filament_brand_code["brand_code"]

    # TODO: test sub_brand_code
    # ams_message["print"]["tray_sub_brands"] = filament_brand_code["sub_brand_code"]
    ams_message["print"]["tray_sub_brands"] = ""

    print(ams_message)
    publish(getMqttClient(), ams_message)

    return redirect(url_for('home', success_message=f"Updated Spool ID {spool_id} with TAG id {tag_id} to AMS {ams_id}, Tray {tray_id}."))
  except Exception as e:
    traceback.print_exc()
    return render_template('error.html', exception=str(e))


@app.route("/")
def home():
  try:
    last_ams_config = getLastAMSConfig()
    ams_data = last_ams_config.get("ams", [])
    vt_tray_data = last_ams_config.get("vt_tray", {})
    spool_list = fetchSpools()
    success_message = request.args.get("success_message")

    issue = False
    #TODO: recheck tray ID and external spool ID and extract it to constant
    augmentTrayDataWithSpoolMan(spool_list, vt_tray_data, trayUid(vt_tray_data["id"], 255))
    issue |= vt_tray_data["issue"]

    for ams in ams_data:
      for tray in ams["tray"]:
        augmentTrayDataWithSpoolMan(spool_list, tray, trayUid(ams["id"], tray["id"]))
        issue |= tray["issue"]

    return render_template('index.html', success_message=success_message, ams_data=ams_data, vt_tray_data=vt_tray_data, color_is_dark=color_is_dark, AUTO_SPEND=AUTO_SPEND, issue=issue)
  except Exception as e:
    traceback.print_exc()
    return render_template('error.html', exception=str(e))

@app.route("/assign_tag")
def assign_tag():
  try:
    spools = fetchSpools()

    return render_template('assign_tag.html', spools=spools)
  except Exception as e:
    traceback.print_exc()
    return render_template('error.html', exception=str(e))

@app.route("/write_tag")
def write_tag():
  try:
    spool_id = request.args.get("spool_id")

    if not spool_id:
      return "spool ID is required as a query parameter (e.g., ?spool_id=1)"

    myuuid = str(uuid.uuid4())

    patchExtraTags(spool_id, {}, {
      "tag": json.dumps(myuuid),
    })
    return render_template('write_tag.html', myuuid=myuuid, BASE_URL=BASE_URL)
  except Exception as e:
    traceback.print_exc()
    return render_template('error.html', exception=str(e))

@app.route('/', methods=['GET'])
def health():
  return "OK", 200
