"""Demo fleet vehicles for transport operator monitoring."""

DEMO_FLEET = [
    {"id": "BUS-101", "type": "bus", "driver": "S. Nkosi", "corridor": "Durban CBD → Umlazi"},
    {"id": "BUS-204", "type": "bus", "driver": "T. Pillay", "corridor": "Durban Station → UKZN"},
    {"id": "TAXI-07", "type": "taxi", "driver": "M. Dlamini", "corridor": "Warwick Junction → Pinetown"},
    {"id": "VAN-12", "type": "delivery", "driver": "L. Mthembu", "corridor": "Durban Harbour → Umhlanga"},
    {"id": "BUS-305", "type": "bus", "driver": "R. Govender", "corridor": "Chatsworth → Durban CBD"},
]

# Key corridors to auto-check for route safety status
KEY_CORRIDORS = [
    ("Durban CBD", "Umlazi"),
    ("Durban Station", "UKZN"),
    ("Pinetown", "Durban CBD"),
    ("Warwick Junction", "Durban Station"),
    ("Umhlanga", "Durban CBD"),
    ("Chatsworth", "Phoenix"),
]
