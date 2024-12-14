import requests
import zipfile
import tempfile
import xml.etree.ElementTree as ET

def getFilamentsUsageFrom3mf(url):
  """
  Download a 3MF file from a URL, unzip it, and parse filament usage.

  Args:
      url (str): URL to the 3MF file.

  Returns:
      list[dict]: List of dictionaries with `tray_info_idx` and `used_g`.
  """
  try:
    # Create a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".3mf") as temp_file:
      temp_file_name = temp_file.name
      print("Downloading 3MF file...")

      # Download the file and save it to the temporary file
      response = requests.get(url)
      response.raise_for_status()
      temp_file.write(response.content)
      print(f"3MF file downloaded and saved as {temp_file_name}.")

    # Unzip the 3MF file
    with zipfile.ZipFile(temp_file_name, 'r') as z:
      # Check for the Metadata/slice_info.config file
      slice_info_path = "Metadata/slice_info.config"
      if slice_info_path in z.namelist():
        with z.open(slice_info_path) as slice_info_file:
          # Parse the XML content of the file
          tree = ET.parse(slice_info_file)
          root = tree.getroot()

          # Extract id and used_g from each filament
          result = []
          for plate in root.findall(".//plate"):
            for filament in plate.findall(".//filament"):
              used_g = filament.attrib.get("used_g")
              if used_g:
                result.append(used_g)
              else:
                result.append('0.0')
          return result
      else:
        print(f"File '{slice_info_path}' not found in the archive.")
        return []
  except requests.exceptions.RequestException as e:
    print(f"Error downloading file: {e}")
    return []
  except zipfile.BadZipFile:
    print("The downloaded file is not a valid 3MF archive.")
    return []
  except ET.ParseError:
    print("Error parsing the XML file.")
    return []
  except Exception as e:
    print(f"An unexpected error occurred: {e}")
    return []
  finally:
    # Cleanup: Delete the temporary file
    try:
      import os
      if os.path.exists(temp_file_name):
        os.remove(temp_file_name)
    except Exception as cleanup_error:
      print(f"Error during cleanup: {cleanup_error}")
