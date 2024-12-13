import json
import uuid

from flask import Flask, request, render_template_string

from config import BASE_URL
from filament import generate_filament_brand_code, generate_filament_temperatures
from messages import AMS_FILAMENT_SETTING
from mqtt_bambulab import fetchSpools, getLastAMSConfig, publish, getMqttClient, setActiveTray
from spoolman_client import patchExtraTags, getSpoolById

app = Flask(__name__)


@app.route("/spool_info")
def spool_info():
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

  # Generate HTML for AMS selection
  html = f"""
    <h1>Spool information</h1>
    """
  if current_spool:
    html += f"<p>Current Spool: {current_spool}</p>"
  html += """
    <h1>AMS</h1>
    <ul>
    """

  for ams in ams_data:
    html += f"<li>AMS {ams['id']} (Humidity: {ams['humidity']}%, Temp: {ams['temp']}°C)<ul>"
    for tray in ams["tray"]:
      tray_status = f"[{tray['tray_sub_brands']} {tray['tray_color']}]"
      html += f"""
            <li>
                Tray {tray['id']} {tray_status} - Remaining: {tray['remain']}%
                <a href="/tray_load?spool_id={current_spool['id']}&tag_id={tag_id}&ams={ams['id']}&tray={tray['id']}">Pick this tray</a>
            </li>
            """
    html += "</ul></li>"
  html += "</ul>"
  html += f"""
            <h1>External Spool</h1>
            <ul>
              <li>Tray {vt_tray_data['id']} [{vt_tray_data['tray_sub_brands']} {vt_tray_data['tray_color']}] - Remaining: {vt_tray_data['remain']}%
                <a href="/tray_load?spool_id={current_spool['id']}&tag_id={tag_id}&ams={vt_tray_data['id']}&tray=255">Pick this tray</a></li>
            </ul>
          """

  return render_template_string(html)


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

    return f"""
        <h1>Success</h1>
        <p>Updated Spool ID {spool_id} with TAG id {tag_id} to AMS {ams_id}, Tray {tray_id}.</p>
        """
  except Exception as e:
    return f"<h1>Error</h1><p>{str(e)}</p>"


@app.route("/")
def home():
  try:
    spools = fetchSpools()

    last_ams_config = getLastAMSConfig()
    ams_data = last_ams_config.get("ams", [])
    vt_tray_data = last_ams_config.get("vt_tray", {})

    html = """
      <h1>Current AMS Configuration</h1>
      """
    html += """
    <h1>AMS</h1>
    <ul>
    """

    for ams in ams_data:
      html += f"<li>AMS {ams['id']} (Humidity: {ams['humidity']}%, Temp: {ams['temp']}°C)<ul>"
      for tray in ams["tray"]:
        tray_status = f"[{tray['tray_sub_brands']} {tray['tray_color']}]"
        html += f"""
              <li>
                  Tray {tray['id']} {tray_status} - Remaining: {tray['remain']}%
              </li>
              """
      html += "</ul></li>"
    html += "</ul>"
    html += f"""
              <h1>External Spool</h1>
              <ul>
                <li>Tray {vt_tray_data['id']} [{vt_tray_data['tray_sub_brands']} {vt_tray_data['tray_color']}] - Remaining: {vt_tray_data['remain']}%</li>
              </ul>
            """
    html += """  
      <h1>Add new TAG</h1>
      <ul>
      """
    for spool in spools:
      if not spool.get("extra", {}).get("tag"):
        html += f"<li><a href='/assign_tag?spool_id={spool.get('id')}'>Spool {spool.get('filament').get('vendor').get('name')} - {spool.get('filament').get('name')}</a></li>"
    html += "</ul>"
    return html
  except Exception as e:
    return f"<h1>Error</h1><p>{str(e)}</p>"


@app.route("/assign_tag")
def assign_tag():
  spool_id = request.args.get("spool_id")

  if not spool_id:
    return "spool ID is required as a query parameter (e.g., ?spool_id=1)"

  myuuid = str(uuid.uuid4())

  patchExtraTags(spool_id, {}, {
    "tag": json.dumps(myuuid),
  })

  return f"""
  <html>
  <header>
        <script type="text/javascript">
        function writeNFC(){{
          const ndef = new NDEFReader();
          ndef.write({{
            records: [{{ recordType: "url", data: "{BASE_URL}/spool_info?tag_id={myuuid}" }}],
          }}).then(() => {{
            alert("Message written.");
          }}).catch(error => {{
            alert(`Write failed :-( try again: ${{error}}.`);
          }}); 
        }};
        </script>
        </header>
        <body>
        NFC Write
        <button id="write" onclick="writeNFC()">Write</button>
        </body>
        </html>
        """


@app.route('/', methods=['GET'])
def health():
  return "OK", 200
