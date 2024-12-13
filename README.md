# OpenSpoolMan
Use any filament like Bambu filaments with automatic recognition and filament usage updates in your AMS!

No need for cloud or any special hardware, just your phone and some NFC tags!

Similar functionality to https://github.com/spuder/OpenSpool using only your phone, server and NFC tags integrated with SpoolMan

Everything works locally without cloud access, you can use scripts/init_bambulab.py script to access your PRINTER_ID and PRINTER_CODE if it is not available on your printer.

### What you need:
 - Android Phone with Chrome web browser or iPhone (manual process much more complicated)
 - Server to run OpenSpoolMan with https that is reachable from your Phone and can reach both SpoolMan and Bambu Lab printer on the network
 - Active Bambu Lab Account or PRINTER_ID and PRINTER_CODE on your printer
 - Bambu Lab printer https://eu.store.bambulab.com/collections/3d-printer
 - SpoolMan installed https://github.com/Donkie/Spoolman
 - NFC Tags https://eu.store.bambulab.com/en-sk/collections/nfc/products/nfc-tag-with-adhesive https://www.aliexpress.com/item/1005006332360160.html

### How to setup:
 - Rename config.env.template to config.env or set environment properies and: 
   - set OPENSPOOLMAN_BASE_URL - that is the URL where OpenSpoolMan will be available on your network. Must be https for NFC write to work. without trailing slash
   - set PRINTER_ID - On your printer clicking on Setting -> Device -> Printer SN
   - set PRINTER_ACCESS_CODE - On your printer clicking on Setting -> Lan Only Mode -> Access Code (you _don't_ need to enable the LAN Only Mode)
   - set PRINTER_IP - On your printer clicking on Setting -> Lan Only Mode -> IP Address (you _don't_ need to enable the LAN Only Mode)
   - set SPOOLMAN_BASE_URL - according to your SpoolMan installation without trailing slash
 - Run the server (wsgi.py)
 - Run Spool Man
 - Add following extra Fields to your SpoolMan:
   - Filaments
     - "type","Type","Choice","Basic","Silk, Basic, High Speed, Matte, Plus, Flexible, Translucent","No"
     - "nozzle_temperature","Nozzle Temperature","Integer Range","°C","190 – 230"
   - Spools
     - "tag","tag","Text"
     - "active_tray","Active Tray","Text
 - Add your Manufacturers, Filaments and Spools to Spool Man (when adding filament you can try "Import from External" for faster workflow)
 - Open the server base url in browser on your mobile phone
 - Optionally add Bambu Lab RFIDs to extra tag on your Bambu Spools so they will be matching. You can get the tag id from logs or from browser in AMS info.
 - For non Bambu Lab filaments click on the filament and click Write and hold empty NFC tag to your phone (allow NFC in popup if prompted)
 - Attach NFC tag to your filament
 - Load filament to your AMS by loading it and then putting your phone near NFC tag and allowing your phone to open the website
 - On the website pick the slot you put your filament in
 - Done

### Deployment
Run locally in venv by configuring environment properties and running wsgi.py, supports adhoc ssl.

Run in docker by configuring config.env and running compose.yaml, you will need more setup/config to run ssl.

Run in kubernetes using helm chart, where you can configure the ingress with SSL. https://github.com/truecharts/public/blob/master/charts/library/common/values.yaml

### Notes:
 - If you change the BASE_URL of this app, you will need to reconfigure all NFC TAGS

### TBD:
 - Filament remaining in AMS (I have only AMS lite, if you have AMS we can test together)
 - Filament spending based on printing
 - Evidently needed GUI improvements
 - Code cleanup
 - Video showcase
 - Docker compose SSL
 - TODOs
