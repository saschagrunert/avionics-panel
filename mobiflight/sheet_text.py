"""What each control does in each profile, in a few plain words, for the aircraft cheat sheets (sheet.py,
docs/using/aircraft/). The words are written by hand from the profiles' tables and docs/using/mapping.md. A text is
None where the profile maps nothing; tests/test_sheet.py checks that much against the tables (a control the profile
maps has a text, one it leaves unmapped has none), not the words themselves.

The texts are keyed by the panel's controls (sheet.CONTROLS): a key by its button and its shifted button
(firmware/buttonmap.py's names), a knob by its rings and push, plain and with SHIFT. They come in blocks as the
families are built from parts: the radios and audio every profile shares, then an autopilot, a cockpit and a
navigator. The details and the reasons are in docs/using/mapping.md.
"""
from mobiflight.families.parts import VFR

SHIFT = "next key or knob: its ⇧ function; held 1 s: locked"

# ---------------- every profile: audio, radios, transponder, the FREQ knob ----------------
RADIOS = {
    "MIC1": "talk on, hear COM 1",
    "ADF_AUDIO": "listen to the ADF ident",
    "COM1": "listen, on or off; kept if talked on",
    "NAV1_AUDIO": "listen to the NAV 1 ident",
    "COM_SWAP": "COM flip-flop",
    "COM_121_5": "tune COM to 121.5",
    "MIC2": "talk on, hear COM 2",
    "DME_AUDIO": "listen to the DME ident",
    "COM2": "listen, on or off; kept if talked on",
    "NAV2_AUDIO": "listen to the NAV 2 ident",
    "VFR": f"squawk {VFR} and ALT; again: the code before",
    "IDENT": "IDENT",
    "NAV_SWAP": "NAV flip-flop",
    "ADF_SWAP": "ADF flip-flop",
    "FREQ_OUTER": "MHz (COM, NAV); ADF 100 kHz",
    "FREQ_INNER": "kHz (COM, NAV); ADF 1 kHz, quick turn 10 kHz",
    "FREQ_PUSH": "COM, NAV, ADF (green light: off, on, blinks); held 1 s: COM",
    "SQUAWK": "outer picks a digit, inner sets it; then VFR: IDENT",
    "XPDR": "transponder standby or ALT",
}

# the ALT/HDG knob as the simulator's autopilot and instruments have it
ALT_HDG = {
    "ALT_KNOB": "selected altitude: 100 ft, quick turn 1000 ft",
    "HDG_KNOB": "heading bug: 1°, quick turn 10°",
    "SYNC": "heading bug to the heading",
    "BARO": "altimeter setting",
}

# ---------------- autopilots ----------------
GFC700 = {
    "AP": "autopilot on or off",
    "TEST": None,
    "ALT": "ALT hold",
    "ARM": "PFD Tmr/Ref window (minimums)",
    "HDG": "HDG mode",
    "FD": "flight director (only with AP off)",
    "YD": "yaw damper",
    "VNV": "VNAV",
    "S_VNV": "VNAV",
    "NAV": "NAV mode",
    "GPSS": None,
    "UP": "nose up: VS, IAS or pitch",
    "S_UP": "nose up, no repeat",
    "VS": "VS mode",
    "S_VS": "VS mode",
    "APR": "approach",
    "BC": "back course",
    "DN": "nose down: VS, IAS or pitch",
    "S_DN": "nose down, no repeat",
    "FLC": "FLC mode",
    "S_FLC": "FLC mode",
    "LVL": "wings and pitch level, engages AP",
    "HALF_BANK": None,
}

GFC500 = {
    **GFC700,
    "ARM": None,
    "BC": None,
    "FLC": "IAS mode",
    "S_FLC": "IAS mode",
}

KAP140 = {
    "AP": "autopilot on or off",
    "TEST": None,
    "ALT": "ALT hold",
    "ARM": None,
    "HDG": "HDG mode",
    "FD": None,
    "YD": None,
    "VNV": "to waypoint: works out, sets VS",
    "S_VNV": "to waypoint: works out, sets VS",
    "NAV": "NAV mode",
    "GPSS": None,
    "UP": "VS rate up",
    "S_UP": "UP, no repeat",
    "VS": "VS: leaves ALT hold for VS",
    "S_VS": "VS: leaves ALT hold for VS",
    "APR": "APR mode",
    "BC": "REV (back course)",
    "DN": "VS rate down",
    "S_DN": "DN, no repeat",
    "FLC": None,
    "S_FLC": None,
    "LVL": None,
    "HALF_BANK": None,
}
KAP140_KNOB = {"ALT_KNOB": "KAP 140 altitude: 100 ft, quick turn 1000 ft"}

KFC150 = {
    "AP": "KFC 150 AP ENG",
    "TEST": "self-test, AP off only; held: MD41 lamp test",
    "ALT": "ALT hold",
    "ARM": "KAS 297B ALT ARM",
    "HDG": "HDG mode",
    "FD": "flight director (only with AP off)",
    "YD": "yaw damper, if fitted",
    "VNV": "to waypoint: sets VS, VS ENG",
    "NAV": "NAV mode",
    "UP": "rocker: ALT, VS or pitch up",
    "VS": "KAS 297B VS ENG",
    "S_VS": "KAS 297B VS ENG",
    "APR": "APR mode",
    "BC": "BC mode",
    "DN": "rocker: ALT, VS or pitch down",
    "FLC": None,
    "S_FLC": None,
    "LVL": None,
    "HALF_BANK": None,
    "GPSS": None,
    "S_VNV": "to waypoint: sets VS, VS ENG",
    "S_UP": "rocker up",
    "S_DN": "rocker down",
}
KFC150_KNOB = {"ALT_KNOB": "KAS 297B altitude (rate with its knob pulled)"}

# ---------------- cockpits: the knobs round the autopilot, lighting ----------------
NO_DIMMERS = {"PANEL": None, "FLOOD": None, "CABIN": "cabin lights"}

G1000_COCKPIT = {
    "CRS_CTR": "centre the course (CRS push)",
    "STD": "STD; again: the setting before (PFD Opt, STD Baro)",
    "CRS": "PFD CRS knob; quick turn 10°",
    "BARO": "PFD BARO knob",
    **NO_DIMMERS,
}

BENDIX_KING = {
    "CRS_CTR": "NAV 1 course to the VOR or LOC",
    "CRS": "NAV 1 course: 1°, quick turn 10°",
    "XPDR": "KT 76: SBY or ALT",
    "STD": "STD; again: the setting before",
    **NO_DIMMERS,
}
G3X_COCKPIT = {
    "CRS_CTR": "centre a VOR or LOC course",
    "CRS": "course of the CDI; quick turn 10°",
    "STD": "STD",
    "XPDR": "standby or ALT (G3X may pick ground mode)",
    **NO_DIMMERS,
}

# ---------------- navigators ----------------
G1000_NAV = {
    "CDI": "GPS, NAV 1, NAV 2",
    "OBS": "GPS OBS mode",
    "HOME": "MFD engine menu; again: back",
    "FPL": "FPL",
    "VNAV": "MFD map: Detail (declutter)",
    "DIRECT": "D→",
    "MSG": "PFD Alerts window",
    "MENU": "MENU",
    "NRST": "PFD Nearest window",
    "PROC": "PROC",
    "TERR": "MFD map: Checklist softkey",
    "CLR": "CLR",
    "MAP": "MFD map: Charts",
    "ENT": "ENT",
    "S_ENT": "ENT",
    "FMS_OUTER": "FMS outer knob",
    "FMS_INNER": "FMS inner knob",
    "CRSR": "cursor (FMS push)",
    "RANGE": "MFD map range",
    "PAN_UD": "pan the MFD map",
    "PAN_LR": "pan the MFD map",
    "PTR": "map pointer",
    "S_RANGE": "PFD inset map range",
    "S_PAN_UD": "pan the PFD inset map",
    "S_PAN_LR": "pan the PFD inset map",
    "S_PTR": "inset map pointer",
}
G1000_UNIT2 = "unit 2 is the PFD: FMS keys and knob, COM 2 / NAV 2"

G3X_NAV = {
    "CDI": "GPS or NAV 1",
    "OBS": "OBS mode",
    "HOME": None,
    "FPL": None,
    "VNAV": None,
    "DIRECT": "D→",
    "MSG": None,
    "MENU": "MENU",
    "NRST": "NRST",
    "PROC": None,
    "TERR": None,
    "CLR": "BACK",
    "MAP": None,
    "ENT": None,
    "S_ENT": None,
    "FMS_OUTER": "right knob, outer",
    "FMS_INNER": "right knob, inner",
    "CRSR": "right knob push",
    "RANGE": None,
    "PAN_UD": None,
    "PAN_LR": None,
    "PTR": None,
    "S_RANGE": None,
    "S_PAN_UD": None,
    "S_PAN_LR": None,
    "S_PTR": None,
}
G3X_UNIT2 = "unit 2 is the MFD, with COM 2 / NAV 2"

GNS_NAV = {
    "CDI": "GNS CDI: GPS or VLOC",
    "OBS": "GNS OBS",
    "HOME": None,
    "FPL": "FPL",
    "VNAV": "VNAV (GNS 530, unit 1)",
    "DIRECT": "D→",
    "MSG": "MSG",
    "MENU": "MENU",
    "NRST": None,
    "PROC": "PROC",
    "TERR": None,
    "CLR": "CLR",
    "MAP": "CLR held: default map page",
    "ENT": "ENT",
    "S_ENT": "ENT",
    "FMS_OUTER": "large right knob",
    "FMS_INNER": "small right knob",
    "CRSR": "CRSR (knob push)",
    "RANGE": "GNS 530 RNG (clockwise zooms out)",
    "PAN_UD": "COM 1 volume",
    "PAN_LR": None,
    "PTR": None,
    "S_RANGE": "GNS 430 RNG",
    "S_PAN_UD": "COM 2 volume",
    "S_PAN_LR": None,
    "S_PTR": None,
}
GNS_UNIT2 = "unit 2 is the GNS 430, with COM 2 / NAV 2"

GTN_NAV = {
    "CDI": None,
    "OBS": None,
    "HOME": "HOME",
    "FPL": None,
    "VNAV": None,
    "DIRECT": "D→",
    "MSG": None,
    "MENU": None,
    "NRST": None,
    "PROC": None,
    "TERR": None,
    "CLR": None,
    "MAP": None,
    "ENT": None,
    "S_ENT": None,
    "FMS_OUTER": "large knob",
    "FMS_INNER": "small knob",
    "CRSR": "knob push: COM or NAV; held: flip",
    "RANGE": "GTN 750 map zoom (clockwise out)",
    "PAN_UD": "GTN 750 volume",
    "PAN_LR": None,
    "PTR": "GTN 750 volume push: squelch, or ident with NAV",
    "S_RANGE": "GTN 650 map zoom",
    "S_PAN_UD": "GTN 650 volume",
    "S_PAN_LR": None,
    "S_PTR": "GTN 650 volume push: squelch, or ident with NAV",
}
GTN_UNIT2 = "unit 2 is the GTN 650Xi, with COM 2 / NAV 2"

BONANZA_NAV = {
    "CDI": "GPS or VLOC (GNS, HSI, MD41)",
    "OBS": "GNS OBS",
    "HOME": "GTN HOME",
    "FPL": "FPL (GNS)",
    "VNAV": "VNAV (GNS 530, unit 1)",
    "DIRECT": "D→",
    "MSG": "MSG",
    "MENU": "MENU (KLN 90B: ALT)",
    "NRST": "MD41 APR ARM (unit 1)",
    "PROC": "PROC (GNS; PMS50 GTN: procedures)",
    "TERR": "MD41 OBS (unit 1)",
    "CLR": "CLR",
    "MAP": "CLR held: default map page",
    "ENT": "ENT",
    "S_ENT": "ENT",
    "FMS_OUTER": "navigator's outer right knob",
    "FMS_INNER": "navigator's inner right knob",
    "CRSR": "CRSR (GTN: COM or NAV)",
    "RANGE": "map range; KLN 90B left inner knob",
    "PAN_UD": "COM 1 / GTN volume",
    "PAN_LR": "KLN 90B left outer knob",
    "PTR": "GTN volume push; KLN 90B left CRSR",
    "S_RANGE": "map range of the secondary",
    "S_PAN_UD": "COM 2 / GTN 650 volume",
    "S_PAN_LR": "weather radar range",
    "S_PTR": "GTN 650 volume push",
}
BONANZA_UNIT2 = "unit 2 is the secondary (GNS 430, GTN 650 or KX 155B)"

BONANZA = {
    "BARO": "both altimeters' setting, 0.01 inHg",
    "STD": "STD on both; again: the setting before",
    "XPDR": "GTX 327: ALT or STBY",
    "VFR": f"squawk {VFR} and GTX ALT; again: the code before",
    "MIC1": "talk on, hear COM 1 (and the selector)",
    "MIC2": "talk on, hear COM 2 (and the selector)",
    "GPSS": "HSI source: NAV 1 or RNAV",
    "FLC": "radar antenna down 5 %",
    "S_FLC": "KR 87 ADF (antenna) key",
    "S_VNV": "KR 87 BFO key",
    "LVL": "KDI 572R DME selector, next",
    "HALF_BANK": "radar antenna up 5 %",
    "S_UP": "EDM 800 STEP; held: long press",
    "S_DN": "EDM 800 LEAN FIND; held: long press",
    "ADF_SWAP": "KR 87 FRQ",
    "PANEL": "instrument lights, 5 % steps",
    "FLOOD": "glareshield flood and yoke light",
    "CABIN": "reading lights",
}

# ---------------- the profiles ----------------
SHEETS = {
    "g1000": ({**RADIOS, **ALT_HDG, **GFC700, **G1000_COCKPIT, **G1000_NAV}, G1000_UNIT2),
    "g3x": ({**RADIOS, **ALT_HDG, **GFC500, **G3X_COCKPIT, **G3X_NAV}, G3X_UNIT2),
    "gns": ({**RADIOS, **ALT_HDG, **KAP140, **KAP140_KNOB, **BENDIX_KING, **GNS_NAV}, GNS_UNIT2),
    "gtn": ({**RADIOS, **ALT_HDG, **KAP140, **KAP140_KNOB, **BENDIX_KING, **GTN_NAV}, GTN_UNIT2),
    "black-square-bonanza": ({**RADIOS, **ALT_HDG, **KFC150, **KFC150_KNOB, **BENDIX_KING, **BONANZA_NAV,
                              **BONANZA}, BONANZA_UNIT2),
    "cows-da40": ({**RADIOS, **ALT_HDG, **GFC700, **G1000_COCKPIT, **G1000_NAV,
                   "BARO": "PFD BARO knob and the standby",
                   "STD": "STD on both; again: back (PFD Opt, STD Baro)",
                   "PANEL": "panel lights, 5 % steps", "FLOOD": "glareshield lights, 5 % steps",
                   "CABIN": "the three cabin lights"}, G1000_UNIT2),
    "carenado-c182t": ({**RADIOS, **ALT_HDG, **KAP140, **KAP140_KNOB, **G1000_COCKPIT, **G1000_NAV,
                        "VNV": "to waypoint: NXi VSR or works it out",
                        "S_VNV": "to waypoint: NXi VSR or works it out",
                        "PANEL": "all panel lights, 5 % steps", "FLOOD": "cabin lights, 5 % steps",
                        "CABIN": "the two cabin lights"}, G1000_UNIT2),
}
