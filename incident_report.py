import streamlit as st
import pandas as pd
import datetime
from db_utils import (
    save_incident_report,
    save_incident_image,
    get_recent_incident_reports,
    get_incident_images,
)
import io
import json
import re
from PIL import Image, ExifTags
import zipfile

# dynamic import of pytesseract to avoid static import error (Pylance)
# If you want OCR, install pytesseract in the environment and the Tesseract binary on the OS.
try:
    import importlib
    pytesseract = importlib.import_module("pytesseract")
except Exception:
    pytesseract = None

# new: vehicle code mapping (KP1->patrol car, etc.)
VEHICLE_MAP = {
    "KP1": "KDK 825Y",
    "KP2": "KDS 374F",
    "KP3": "KDG 320Z",
}

# helper: parse captions input (JSON or lines "filename::caption" or "filename|caption")
def _parse_captions_input(text):
    if not text:
        return {}
    text = text.strip()
    # try JSON mapping first
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return {k: str(v) for k, v in obj.items()}
    except Exception:
        pass
    mapping = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # try separators :: or |
        if "::" in line:
            fname, cap = line.split("::", 1)
        elif "|" in line:
            fname, cap = line.split("|", 1)
        else:
            # if only caption provided, use special key "_all"
            mapping["_all"] = mapping.get("_all", "") + (" " + line if mapping.get("_all") else line)
            continue
        mapping[fname.strip()] = cap.strip()
    return mapping

# helper: normalize and compress image
def _normalize_image(image_bytes, quality=75):
    """
    Normalize image to standard JPEG format, compress, and return bytes.
    This fixes issues with WhatsApp images and reduces file size.
    """
    try:
        # Open image
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if necessary (removes alpha channel, fixes CMYK issues)
        if img.mode not in ('RGB', 'L'):
            img = img.convert('RGB')

        # Auto-rotate based on EXIF orientation
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == 'Orientation':
                    break
            exif = img._getexif()
            if exif is not None:
                orientation = exif.get(orientation, 1)
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)
        except Exception:
            pass  # Skip rotation if EXIF reading fails

        # Compress and save as JPEG
        output = io.BytesIO()
        img.save(output, format='JPEG', quality=quality, optimize=True)
        return output.getvalue()

    except Exception as e:
        # If normalization fails, return original bytes
        print(f"Image normalization failed: {e}")
        return image_bytes

# helper: EXIF datetime
def _get_exif_datetime(img):
    try:
        exif = img._getexif()
        if not exif:
            return None
        for tag, val in exif.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded in ("DateTimeOriginal", "DateTime"):
                # format "YYYY:MM:DD HH:MM:SS"
                try:
                    return datetime.datetime.strptime(val, "%Y:%m:%d %H:%M:%S")
                except Exception:
                    try:
                        # sometimes contains timezone or other format; attempt ISO parse
                        return datetime.datetime.fromisoformat(val.replace("Z", "+00:00"))
                    except Exception:
                        continue
    except Exception:
        return None
    return None

# helper: convert GPS tuple to degrees
def _convert_to_degrees(value):
    # value is typically ((deg_num,deg_den),(min_num,min_den),(sec_num,sec_den))
    try:
        d = value[0][0] / value[0][1]
        m = value[1][0] / value[1][1]
        s = value[2][0] / value[2][1]
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None

# helper: EXIF GPS extraction
def _get_exif_gps(img):
    try:
        exif = img._getexif()
        if not exif:
            return None
        gps_info = {}
        for tag, val in exif.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                for t in val:
                    sub_decoded = ExifTags.GPSTAGS.get(t, t)
                    gps_info[sub_decoded] = val[t]
        if not gps_info:
            return None
        lat = _convert_to_degrees(gps_info.get("GPSLatitude")) if gps_info.get("GPSLatitude") else None
        lon = _convert_to_degrees(gps_info.get("GPSLongitude")) if gps_info.get("GPSLongitude") else None
        lat_ref = gps_info.get("GPSLatitudeRef")
        lon_ref = gps_info.get("GPSLongitudeRef")
        if lat and lat_ref and lat_ref.upper() == "S":
            lat = -lat
        if lon and lon_ref and lon_ref.upper() == "W":
            lon = -lon
        if lat and lon:
            return {"latitude": lat, "longitude": lon}
    except Exception:
        return None
    return None

# helper: extract images and chat text from a whatsapp export zip
def _process_whatsapp_zip(zip_bytes):
    """
    Return list of dicts: [{"name": filename, "data": bytes, "caption_from_text": optional}]
    Attempts to read any .txt files in the zip as chat history and map captions to image filenames.
    """
    out = []
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            # collect text content
            chat_text = ""
            for info in z.infolist():
                if info.filename.lower().endswith(".txt"):
                    try:
                        chat_text += z.read(info).decode(errors="ignore") + "\n"
                    except Exception:
                        continue
            # collect image files
            for info in z.infolist():
                name = info.filename.rsplit("/", 1)[-1]  # drop folders
                if not name:
                    continue
                if name.lower().endswith((".jpg", ".jpeg", ".png")):
                    try:
                        data = z.read(info)
                    except Exception:
                        continue
                    # try to find a caption line for this filename inside chat_text
                    caption = None
                    if chat_text:
                        # try direct filename match first (line that contains filename)
                        pattern = re.compile(r".*\b" + re.escape(name) + r"\b.*", flags=re.IGNORECASE)
                        m = pattern.search(chat_text)
                        if m:
                            # take the full line that matched
                            line = m.group(0).strip()
                            # try to extract the message part after the colon " - Name: message"
                            parts = re.split(r"\s-\s|\:\s", line, maxsplit=2)
                            if len(parts) >= 3:
                                caption = parts[-1].strip()
                            else:
                                # fallback to whole line
                                caption = line
                        else:
                            # try to find lines referencing "image omitted" or previous message before filename mention
                            # fallback: search for nearby lines where filename base (without ext) appears
                            basename = re.sub(r'\.[^.]+$', '', name)
                            m2 = re.search(rf".*{re.escape(basename)}.*", chat_text, flags=re.IGNORECASE)
                            if m2:
                                caption = m2.group(0).strip()
                    out.append({"name": name, "data": data, "caption_from_text": caption})
    except Exception:
        # on error return empty list so calling code can fallback to normal upload
        return []
    return out

# new: OCR bottom-of-image helper (returns extracted text or empty string)
def _ocr_bottom_text(image_bytes, bottom_frac=0.25):
    """
    Crop bottom `bottom_frac` of the image and return OCR text.
    Returns '' if pytesseract not available or OCR fails.
    """
    if not pytesseract:
        return ""
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        w, h = img.size
        top = int(h * (1 - bottom_frac))
        crop = img.crop((0, top, w, h))
        # optional simple preprocessing
        gray = crop.convert("L")
        # run tesseract
        text = pytesseract.image_to_string(gray)
        return text.strip()
    except Exception:
        return ""

# new: parse OCR/chat text for datetime, coords, vehicle code, description
def _parse_text_for_meta(text):
    """
    Return dict with maybe keys: datetime (datetime obj), latitude (float), longitude (float),
    vehicle_code (str like 'KP1'), description (str)
    """
    out = {"datetime": None, "latitude": None, "longitude": None, "vehicle_code": None, "description": None}
    if not text:
        return out
    t = text

    # try to find vehicle code KP1/KP2/KP3
    m = re.search(r"\b(KP[123])\b", t, flags=re.IGNORECASE)
    if m:
        out["vehicle_code"] = m.group(1).upper()

    # coordinates pattern: look for lat,lon floats
    mcoord = re.search(r"(-?\d{1,3}\.\d+)[,\s]+(-?\d{1,3}\.\d+)", t)
    if mcoord:
        try:
            out["latitude"] = float(mcoord.group(1))
            out["longitude"] = float(mcoord.group(2))
        except Exception:
            pass

    # datetime patterns - try several common formats
    # ISO-like
    mdt = re.search(r"(20\d{2}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}(:\d{2})?)", t)
    if not mdt:
        # dd/mm/YYYY or dd-mm-YYYY with time
        mdt = re.search(r"(\d{1,2}[/-]\d{1,2}[/-]20\d{2}[ ,T]\d{1,2}:\d{2}(:\d{2})?)", t)
    if not mdt:
        # exif-like YYYY:MM:DD HH:MM:SS
        mdt = re.search(r"(20\d{2}:\d{2}:\d{2} \d{1,2}:\d{2}:\d{2})", t)
    if mdt:
        s = mdt.group(1)
        try:
            # normalize separators then parse
            s_norm = s.replace("/", "-").replace(":", "-", 2)  # only first two colons to keep time colons
            # fallback parse attempts
            try:
                out["datetime"] = datetime.datetime.fromisoformat(s.replace(":", "-", 2))
            except Exception:
                try:
                    out["datetime"] = datetime.datetime.strptime(s, "%Y:%m:%d %H:%M:%S")
                except Exception:
                    # last resort: extract numbers manually
                    nums = re.findall(r"\d+", s)
                    if len(nums) >= 5:
                        y, mo, d, hh, mm = nums[0], nums[1], nums[2], nums[3], nums[4]
                        out["datetime"] = datetime.datetime(int(y), int(mo), int(d), int(hh), int(mm))
        except Exception:
            out["datetime"] = None

    # description: take remaining text lines after removing matched datetime/coords
    # simplistic: choose the longest line as description
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    if lines:
        # remove any lines that look like coordinates or datetime or vehicle codes
        candidates = []
        for ln in lines:
            if re.search(r"\b(KP[123])\b", ln, flags=re.IGNORECASE):
                continue
            if re.search(r"\d{1,2}[:/.-]\d{1,2}[:/.-]\d{2,4}", ln):
                continue
            if re.search(r"-?\d{1,3}\.\d+", ln):
                continue
            candidates.append(ln)
        if candidates:
            # pick the longest candidate as likely description
            out["description"] = max(candidates, key=len)
        else:
            out["description"] = lines[0]
    return out

# ---------------- Page Function ----------------
def incident_report_page(patrol_vehicle_options=None):
    st.header("🚨 Incident Reporting")

    if patrol_vehicle_options is None:
        patrol_vehicle_options = ["KDG 320Z", "KDK 825Y", "KDS 374F"]

    # ---------------- Incident Form ----------------
    incident_type = st.selectbox("Incident Type", ["Accident", "Incident"])
    patrol_car = st.selectbox("Select Patrol Car", patrol_vehicle_options)

    with st.form("incident_form", clear_on_submit=True):
        st.subheader("Incident Details")

        col1, col2 = st.columns(2)
        with col1:
            incident_date = st.date_input("Incident Date")
            col_time1, col_time2 = st.columns(2)
            with col_time1:
                incident_hour = st.selectbox("Hour", list(range(24)), key="incident_hour")
            with col_time2:
                incident_minute = st.selectbox("Minute", list(range(60)), key="incident_minute")
            incident_time = f"{incident_hour:02d}:{incident_minute:02d}"
            caller = st.text_input("Caller Name")
            phone_number = st.text_input("Caller Phone Number")
            location = st.text_input("Location")
            bound = st.selectbox("Bound", ["Nairobi Bound", "Thika Bound", "Under Pass", "Over Pass", "Service Lane"])
            chainage = st.text_input("Chainage (km)")

        with col2:
            num_vehicles = st.number_input("Number of Vehicles Involved", min_value=0)
            vehicle_type = st.text_input("Type of Vehicle(s) Involved")
            vehicle_condition = st.text_input("Condition of Vehicle(s)")
            num_injured = st.number_input("Number of Injured", min_value=0)
            cond_injured = st.text_input("Condition of Injured")
            injured_part = st.text_input("Body Part Injured")
            fire_hazard = st.checkbox("Fire Hazard")
            oil_leakage = st.checkbox("Oil Leakage")
            chemical_leakage = st.checkbox("Chemical Leakage")
            damage_road_furniture = st.text_area("Damaged Road Furniture")

        st.subheader("Response Details")
        col3, col4 = st.columns(2)
        with col3:
            response_date = st.date_input("Response Date", value=incident_date)
            response_time_val = st.time_input("Response Time", value=datetime.time(int(incident_hour), int(incident_minute)), step=300)
        with col4:
            clearing_date = st.date_input("Clearing Date", value=incident_date)
            clearing_time_val = st.time_input("Clearing Time", step=300)

        department_contact = st.multiselect("Department Contacted", ["KeNHA", "Police", "Engineer", "Highway Patrol Unit", "Ambulance", "Recovery Vehicle", "Hospital"])
        description = st.text_area("Incident Description")

        st.subheader("Incident Information Resource")
        incident_info_resource = st.multiselect("Incident Information Resource", ["KeNHA", "Police", "Engineer", "Road User", "Highway Patrol Unit", "Others"])

        uploaded_photos = st.file_uploader(
            "Upload Incident Photos",
            accept_multiple_files=True,
            type=["jpg", "jpeg", "png"]
        )

        submitted = st.form_submit_button("💾 Save Incident Report")
        if submitted:
            try:
                response_datetime = datetime.datetime.combine(response_date, response_time_val)
                clearing_datetime = datetime.datetime.combine(clearing_date, clearing_time_val)

                data = {
                    "incident_date": incident_date,
                    "incident_time": incident_time,
                    "caller": caller,
                    "phone_number": phone_number,
                    "location": location,
                    "bound": bound,
                    "chainage": chainage,
                    "num_vehicles": num_vehicles,
                    "vehicle_type": vehicle_type,
                    "vehicle_condition": vehicle_condition,
                    "num_injured": num_injured,
                    "cond_injured": cond_injured,
                    "injured_part": injured_part,
                    "fire_hazard": "Yes" if fire_hazard else "No",
                    "oil_leakage": "Yes" if oil_leakage else "No",
                    "chemical_leakage": "Yes" if chemical_leakage else "No",
                    "damage_road_furniture": damage_road_furniture,
                    "response_time": response_datetime,
                    "clearing_time": clearing_datetime,
                    "department_contact": ", ".join(department_contact),
                    "description": description,
                    "patrol_car": patrol_car,
                    "incident_type": incident_type,
                    "incident_info_resource": ", ".join(incident_info_resource),
                }

                report_id = save_incident_report(data, uploaded_by="Admin")

                # Save uploaded photos
                if uploaded_photos:
                    for file in uploaded_photos:
                        file_bytes = file.read()
                        # Normalize and compress before saving
                        normalized_bytes = _normalize_image(file_bytes)
                        save_incident_image(report_id, normalized_bytes, file.name)

                st.success("✅ Incident report saved successfully!")

            except Exception as e:
                st.error(f"Error saving incident report: {e}")

    # ---------------- WhatsApp Import Section ----------------
    st.subheader("📲 Import from WhatsApp")
    st.markdown("Upload either WhatsApp images directly or a WhatsApp export ZIP (chat text + media). Captions can be provided as JSON mapping filename->caption or lines like `filename.jpg::caption`. If you provide only captions lines without filenames, they will be applied as a single combined caption to all images.")
    source = st.radio("Source", ["Image files", "WhatsApp ZIP"], horizontal=True)
    whatsapp_files = None
    whatsapp_zip = None
    if source == "Image files":
        whatsapp_files = st.file_uploader("Upload WhatsApp Images", accept_multiple_files=True, type=["jpg", "jpeg", "png"])
    else:
        whatsapp_zip = st.file_uploader("Upload WhatsApp export ZIP", type=["zip"])

    captions_input = st.text_area("Captions mapping (optional)", height=120, placeholder='{"IMG-1234.jpg": "Accident on bridge"} OR IMG-1234.jpg::Accident on bridge')
    process_btn = st.button("Process WhatsApp Uploads")

    # -- NEW: persist processed items in session_state so user can edit/remove before saving --
    if "whatsapp_items" not in st.session_state:
        st.session_state["whatsapp_items"] = []

    # When user clicks Process, populate session_state['whatsapp_items']
    if process_btn:
        files_to_process = []
        if whatsapp_zip:
            try:
                zip_bytes = whatsapp_zip.read()
                extracted = _process_whatsapp_zip(zip_bytes)
                if not extracted:
                    st.warning("No images found in ZIP or failed to read ZIP.")
                else:
                    for item in extracted:
                        files_to_process.append({"name": item["name"], "data": item["data"], "caption_from_text": item.get("caption_from_text")})
            except Exception as e:
                st.error(f"Error reading ZIP: {e}")
        elif whatsapp_files:
            for f in whatsapp_files:
                try:
                    files_to_process.append({"name": f.name, "data": f.read(), "caption_from_text": None})
                except Exception:
                    continue
        else:
            st.warning("Please provide image files or a WhatsApp zip.")

        if files_to_process:
            captions_map = _parse_captions_input(captions_input)
            new_items = []
            for item in files_to_process:
                fname = item["name"]
                raw = item["data"]
                caption_from_text = item.get("caption_from_text")
                # Normalize and compress the image
                normalized_raw = _normalize_image(raw)

                try:
                    img = Image.open(io.BytesIO(normalized_raw))
                except Exception as e:
                    # Don't skip invalid images - mark them as having an error but still process them
                    # Use original raw bytes for display, but normalized for processing
                    new_items.append({"name": fname, "raw": raw, "normalized_raw": normalized_raw, "error": f"invalid image: {str(e)}"})
                    continue

                exif_dt = _get_exif_datetime(img)
                exif_gps = _get_exif_gps(img)
                ocr_text = _ocr_bottom_text(raw)
                ocr_meta = _parse_text_for_meta(ocr_text)
                chat_meta = _parse_text_for_meta(caption_from_text or "")

                incident_dt = exif_dt or ocr_meta.get("datetime") or chat_meta.get("datetime") or None
                if not incident_dt:
                    m = re.search(r"(20\d{2}[-_]?\d{2}[-_]?\d{2})", fname)
                    if m:
                        s = m.group(1).replace("_", "-")
                        try:
                            incident_dt = datetime.datetime.fromisoformat(s)
                        except Exception:
                            incident_dt = None
                if not incident_dt:
                    incident_dt = datetime.datetime.utcnow()

                gps = exif_gps or ({"latitude": ocr_meta["latitude"], "longitude": ocr_meta["longitude"]} if ocr_meta["latitude"] and ocr_meta["longitude"] else None) or ({"latitude": chat_meta["latitude"], "longitude": chat_meta["longitude"]} if chat_meta["latitude"] and chat_meta["longitude"] else None)

                caption = captions_map.get(fname) or captions_map.get(fname.strip()) or caption_from_text or ocr_meta.get("description") or captions_map.get("_all") or f"Imported from WhatsApp: {fname}"
                vehicle_code = (chat_meta.get("vehicle_code") or ocr_meta.get("vehicle_code") or None)
                suggested_patrol_car = VEHICLE_MAP.get(vehicle_code) if vehicle_code else None

                new_items.append({
                    "name": fname,
                    "raw": raw,
                    "normalized_raw": normalized_raw,
                    "exif_dt": exif_dt,
                    "detected_dt": incident_dt,
                    "exif_gps": exif_gps,
                    "merged_gps": gps,
                    "caption_suggest": caption,
                    "vehicle_code": vehicle_code,
                    "suggested_patrol_car": suggested_patrol_car,
                    "error": None,
                    "include": True,
                    "saved": False,
                    "report_id": None,
                })

            # append (do not overwrite existing) so user can process multiple batches and still edit
            st.session_state["whatsapp_items"].extend(new_items)
            st.success(f"Added {len(new_items)} items for review. You can edit, remove, or save them when ready.")

    # Render session_state items for editing/removal/saving
    if st.session_state.get("whatsapp_items"):
        st.info("Review processed WhatsApp images below. Use Remove to delete any item. Uncheck Include to skip saving a specific item.")

        # allow clearing all processed items
        cols_top = st.columns([1, 1, 1])
        with cols_top[0]:
            if st.button("💥 Clear All Processed Items"):
                st.session_state["whatsapp_items"] = []
                st.experimental_rerun()
        with cols_top[1]:
            if st.button("✅ Mark all as included"):
                for it in st.session_state["whatsapp_items"]:
                    it["include"] = True
        with cols_top[2]:
            if st.button("❌ Uninclude all"):
                for it in st.session_state["whatsapp_items"]:
                    it["include"] = False

        editable_items_meta = []
        # iterate with index so removals are easy
        for idx, p in enumerate(list(st.session_state["whatsapp_items"])):
            with st.expander(f"{idx+1}. {p['name']} {'(saved)' if p.get('saved') else ''}", expanded=False):
                # Don't skip items with errors - show them so user can edit and save
                pass

                cols = st.columns([1, 2])
                with cols[0]:
                    if p.get("error"):
                        st.error(f"⚠️ {p['error']}")
                        st.write("Raw bytes preview:")
                        # Show first 200 bytes as hex for debugging
                        raw_bytes = p["raw"]
                        if len(raw_bytes) > 200:
                            st.code(f"First 200 bytes: {raw_bytes[:200].hex()}")
                        else:
                            st.code(f"All {len(raw_bytes)} bytes: {raw_bytes.hex()}")
                    else:
                        try:
                            st.image(p["raw"], use_container_width=True)
                        except Exception as e:
                            st.error(f"Failed to display image: {e}")
                            st.write("Raw bytes preview:")
                            raw_bytes = p["raw"]
                            if len(raw_bytes) > 200:
                                st.code(f"First 200 bytes: {raw_bytes[:200].hex()}")
                            else:
                                st.code(f"All {len(raw_bytes)} bytes: {raw_bytes.hex()}")

                with cols[1]:
                    if p.get("error"):
                        st.markdown(f"**Error:** {p['error']}")
                        st.markdown("**Note:** This image has issues but can still be saved and viewed later.")
                    else:
                        if p.get("exif_dt"):
                            st.markdown(f"**Extracted timestamp (EXIF):** {p['exif_dt'].isoformat(sep=' ')}")
                        else:
                            st.markdown("**Extracted timestamp (EXIF):** _not found_")
                        st.markdown(f"**Detected timestamp (fallback):** {p['detected_dt'].isoformat(sep=' ')}")

                    init_dt = p.get("exif_dt") or p.get("detected_dt") or datetime.datetime.utcnow()
                    date_key = f"wa_date_{idx}"
                    time_key = f"wa_time_{idx}"
                    if date_key not in st.session_state:
                        st.session_state[date_key] = init_dt.date()
                    if time_key not in st.session_state:
                        st.session_state[time_key] = init_dt.time()
                    selected_date = st.date_input("Incident date", value=st.session_state[date_key], key=date_key)
                    selected_time = st.time_input("Incident time", value=st.session_state[time_key], key=time_key)

                    # GPS and location
                    lat_key = f"wa_lat_{idx}"
                    lng_key = f"wa_lng_{idx}"
                    loc_key = f"wa_loc_{idx}"
                    if p.get("exif_gps"):
                        if lat_key not in st.session_state:
                            st.session_state[lat_key] = f"{p['exif_gps']['latitude']:.6f}"
                        if lng_key not in st.session_state:
                            st.session_state[lng_key] = f"{p['exif_gps']['longitude']:.6f}"
                        sel_lat = st.text_input("Latitude", value=st.session_state[lat_key], key=lat_key)
                        sel_lng = st.text_input("Longitude", value=st.session_state[lng_key], key=lng_key)
                        if loc_key not in st.session_state:
                            st.session_state[loc_key] = f"GPS: {sel_lat}, {sel_lng}"
                        location_text = st.text_input("Location text (editable)", value=st.session_state[loc_key], key=loc_key)
                    else:
                        if loc_key not in st.session_state:
                            st.session_state[loc_key] = p.get("merged_gps") and f"GPS: {p['merged_gps']['latitude']:.6f}, {p['merged_gps']['longitude']:.6f}" or ""
                        location_text = st.text_input("Location text (editable)", value=st.session_state[loc_key], key=loc_key)

                    # description and patrol selection
                    desc_key = f"wa_desc_{idx}"
                    if desc_key not in st.session_state:
                        st.session_state[desc_key] = p.get("caption_suggest") or ""
                    desc = st.text_area("Description (editable)", value=st.session_state[desc_key], key=desc_key)

                    patrol_key = f"wa_patrol_{idx}"
                    if patrol_key not in st.session_state:
                        st.session_state[patrol_key] = p.get("suggested_patrol_car") or "Imported"
                    patrol_choice = st.selectbox("Patrol car (detected/choose)", [st.session_state[patrol_key]] + [pc for pc in patrol_vehicle_options if pc != st.session_state[patrol_key]], index=0, key=patrol_key)

                    # new: bound selection
                    bound_key = f"wa_bound_{idx}"
                    if bound_key not in st.session_state:
                        st.session_state[bound_key] = "Nairobi Bound"
                    bound_choice = st.selectbox("Bound", ["Nairobi Bound", "Thika Bound", "Under Pass", "Over Pass", "Service Lane"], index=0, key=bound_key)

                    # new: clearing time
                    clearing_date_key = f"wa_clearing_date_{idx}"
                    clearing_time_key = f"wa_clearing_time_{idx}"
                    if clearing_date_key not in st.session_state:
                        st.session_state[clearing_date_key] = init_dt.date()
                    if clearing_time_key not in st.session_state:
                        st.session_state[clearing_time_key] = init_dt.time()
                    clearing_date = st.date_input("Clearing date", value=st.session_state[clearing_date_key], key=clearing_date_key)
                    clearing_time = st.time_input("Clearing time", value=st.session_state[clearing_time_key], key=clearing_time_key)

                    # new: number of injured
                    num_injured_key = f"wa_num_injured_{idx}"
                    if num_injured_key not in st.session_state:
                        st.session_state[num_injured_key] = 0
                    num_injured = st.number_input("Number of injured", min_value=0, value=st.session_state[num_injured_key], key=num_injured_key)

                    # new: condition of injured
                    cond_injured_key = f"wa_cond_injured_{idx}"
                    if cond_injured_key not in st.session_state:
                        st.session_state[cond_injured_key] = ""
                    cond_injured = st.text_input("Condition of injured", value=st.session_state[cond_injured_key], key=cond_injured_key)

                    # new: incident type
                    incident_type_key = f"wa_incident_type_{idx}"
                    if incident_type_key not in st.session_state:
                        st.session_state[incident_type_key] = "Incident"
                    incident_type_choice = st.selectbox("Incident type", ["Accident", "Incident"], index=1 if st.session_state[incident_type_key] == "Incident" else 0, key=incident_type_key)

                    include_key = f"wa_include_{idx}"
                    if include_key not in st.session_state:
                        st.session_state[include_key] = p.get("include", True)
                    include = st.checkbox("Include this image when saving", value=st.session_state[include_key], key=include_key)

                    # remove button
                    if st.button(f"Remove {p['name']}", key=f"wa_remove_{idx}"):
                        st.session_state["whatsapp_items"].pop(idx)
                        st.experimental_rerun()

                    # store meta for save step
                    editable_items_meta.append({
                        "idx": idx,
                        "name": p["name"],
                        "raw": p.get("normalized_raw", p["raw"]),  # Use normalized for saving, original for display
                        "date_key": date_key,
                        "time_key": time_key,
                        "loc_key": loc_key,
                        "desc_key": desc_key,
                        "patrol_key": patrol_key,
                        "lat_key": lat_key,
                        "lng_key": lng_key,
                        "bound_key": bound_key,
                        "clearing_date_key": clearing_date_key,
                        "clearing_time_key": clearing_time_key,
                        "num_injured_key": num_injured_key,
                        "cond_injured_key": cond_injured_key,
                        "incident_type_key": incident_type_key,
                        "include_key": include_key,
                        "saved_flag": "wa_saved_" + str(idx),
                    })

        # Save selected reports button (saves only included items)
        if editable_items_meta and st.button("💾 Save Selected Reports"):
            save_results = []
            for meta in editable_items_meta:
                include = st.session_state.get(meta["include_key"], True)
                if not include:
                    save_results.append((meta["name"], None, "skipped"))
                    continue
                sel_date = st.session_state.get(meta["date_key"], datetime.date.today())
                sel_time = st.session_state.get(meta["time_key"], datetime.datetime.utcnow().time())
                if isinstance(sel_date, datetime.date) and isinstance(sel_time, datetime.time):
                    response_dt = datetime.datetime.combine(sel_date, sel_time)
                else:
                    response_dt = datetime.datetime.utcnow()
                desc = st.session_state.get(meta["desc_key"], "")
                patrol_car_selected = st.session_state.get(meta["patrol_key"], "Imported")
                loc_text = st.session_state.get(meta["loc_key"], None)
                lat_val = st.session_state.get(meta["lat_key"], None)
                lng_val = st.session_state.get(meta["lng_key"], None)
                lat_f = None
                lng_f = None
                try:
                    if lat_val:
                        lat_f = float(str(lat_val))
                    if lng_val:
                        lng_f = float(str(lng_val))
                except Exception:
                    lat_f = None
                    lng_f = None

                bound_selected = st.session_state.get(meta["bound_key"], "Nairobi Bound")
                clearing_date_sel = st.session_state.get(meta["clearing_date_key"], response_dt.date())
                clearing_time_sel = st.session_state.get(meta["clearing_time_key"], response_dt.time())
                if isinstance(clearing_date_sel, datetime.date) and isinstance(clearing_time_sel, datetime.time):
                    clearing_dt = datetime.datetime.combine(clearing_date_sel, clearing_time_sel)
                else:
                    clearing_dt = None
                num_injured_val = st.session_state.get(meta["num_injured_key"], 0)
                cond_injured_val = st.session_state.get(meta["cond_injured_key"], "")
                incident_type_val = st.session_state.get(meta["incident_type_key"], "Incident")

                data = {
                    "incident_date": response_dt.date(),
                    "incident_time": response_dt.time().strftime("%H:%M:%S"),
                    "caller": "WhatsApp",
                    "phone_number": None,
                    "location": loc_text or (f"GPS: {lat_f:.6f}, {lng_f:.6f}" if lat_f and lng_f else None),
                    "patrol_car": patrol_car_selected,
                    "bound": bound_selected,
                    "chainage": None,
                    "num_vehicles": None,
                    "vehicle_type": None,
                    "vehicle_condition": None,
                    "num_injured": num_injured_val,
                    "cond_injured": cond_injured_val,
                    "injured_part": None,
                    "fire_hazard": "No",
                    "oil_leakage": "No",
                    "chemical_leakage": "No",
                    "damage_road_furniture": None,
                    "response_time": response_dt,
                    "clearing_time": clearing_dt,
                    "department_contact": None,
                    "description": desc,
                    "incident_type": incident_type_val,
                    "incident_info_resource": "WhatsApp",
                }

                try:
                    report_id = save_incident_report(data, uploaded_by="WhatsApp")
                    # upload image bytes
                    raw_bytes = meta.get("raw")
                    save_incident_image(report_id, raw_bytes, meta["name"])
                    # mark saved in session list so user sees saved status (do not remove)
                    # find corresponding session item by name (first match)
                    for it in st.session_state["whatsapp_items"]:
                        if it["name"] == meta["name"]:
                            it["saved"] = True
                            it["report_id"] = report_id
                            break
                    save_results.append((meta["name"], report_id, "ok"))
                except Exception as e:
                    save_results.append((meta["name"], None, f"error: {e}"))

            ok_count = sum(1 for r in save_results if r[2] == "ok")
            st.success(f"Saved {ok_count}/{len(save_results)} reports.")
            for name, rid, status in save_results:
                if status == "ok":
                    st.write(f"- {name} → report_id: {rid}")
                else:
                    st.write(f"- {name} → {status}")

    # ---------------- Recent Reports Section ----------------
    st.subheader("📋 Recent Incident Reports")

    filter_type = st.radio("Filter by Type", ["All", "Accident", "Incident"], horizontal=True)
    df = get_recent_incident_reports(limit=20)

    if not df.empty:
        if filter_type != "All":
            df = df[df["incident_type"] == filter_type]

        st.dataframe(df)

        # ---------------- Images Section ----------------
        st.subheader("🖼️ Incident Photos")
        selected_id = st.selectbox("Select Incident ID to view photos", df["id"].tolist())
        if selected_id:
            images_meta = get_incident_images(selected_id, only_meta=True)  # only metadata
            if images_meta:
                img_name = st.selectbox("Select Image", [img["image_name"] for img in images_meta])
                if st.button("View Selected Image"):
                    images = get_incident_images(selected_id)
                    selected_img = next(img for img in images if img["image_name"] == img_name)
                    # Ensure image_data is proper bytes for Streamlit
                    image_bytes = selected_img["image_data"]
                    if isinstance(image_bytes, memoryview):
                        image_bytes = bytes(image_bytes)
                    elif not isinstance(image_bytes, bytes):
                        image_bytes = bytes(image_bytes)

                    # Validate that we have valid image data before displaying
                    try:
                        # Quick validation - try to open with PIL
                        from PIL import Image
                        import io
                        Image.open(io.BytesIO(image_bytes))
                        st.image(image_bytes, caption=img_name, width='stretch')
                    except Exception as e:
                        st.error(f"❌ Invalid image data for {img_name}: {e}")
                        st.info("This image file appears to be corrupted or in an unsupported format.")

                        # Show hex dump for debugging
                        if len(image_bytes) < 100:
                            st.code(f"First {len(image_bytes)} bytes: {image_bytes.hex()}")
                        else:
                            st.code(f"First 100 bytes: {image_bytes[:100].hex()}")

                        # Try to decode as text to see if it's stored as raw text
                        try:
                            text_content = image_bytes.decode('utf-8', errors='ignore')
                            if len(text_content) > 0 and len(text_content) < 500:
                                st.info("Content appears to be text data:")
                                st.code(text_content[:500])

                                # Check if it looks like hex data that needs decoding
                                if all(c in '0123456789abcdefABCDEF' for c in text_content.strip()):
                                    st.info("This looks like hex-encoded data. Try decoding it:")
                                    try:
                                        decoded_bytes = bytes.fromhex(text_content.strip())
                                        st.code(f"Decoded first 100 bytes: {decoded_bytes[:100].hex()}")
                                        # Try to display the decoded image
                                        try:
                                            from PIL import Image
                                            import io
                                            Image.open(io.BytesIO(decoded_bytes))
                                            st.success("✅ Hex-decoded data is valid image! Displaying:")
                                            st.image(decoded_bytes, caption=f"{img_name} (hex-decoded)", width='stretch')
                                            # Successfully displayed, skip further error processing
                                            st.stop()
                                        except Exception as decode_e:
                                            st.error(f"❌ Hex-decoded data is not a valid image: {decode_e}")
                                    except Exception as hex_e:
                                        st.error(f"❌ Could not decode hex data: {hex_e}")
                        except:
                            pass
                    else:
                        st.info("No images uploaded for this incident.")
                else:
                    st.info("No images uploaded for this incident.")
            else:
                st.info("No incident reports found.")
