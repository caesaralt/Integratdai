# agents/schema_gpt2.py
# JSON schema for structured outputs from the vision model.
FLOORPLAN_SCHEMA = {
    "type": "object",
    "required": ["units", "scale", "symbols", "rooms"],
    "properties": {
        "units": {"type": "string", "enum": ["mm","cm","m","in","ft"]},
        "scale": {"type": "number"},
        "rooms": {
            "type": "array",
            "items": {
                "type":"object",
                "required":["id","name","polygon"],
                "properties":{
                    "id":{"type":"string"},
                    "name":{"type":"string"},
                    "polygon":{"type":"array","items":{
                        "type":"object","properties":{"x":{"type":"number"},"y":{"type":"number"}}}}
                }
            }
        },
        "panels": {
            "type":"array",
            "items":{"type":"object","properties":{
                "id":{"type":"string"},
                "type":{"type":"string"},
                "point":{"type":"object","properties":{"x":{"type":"number"},"y":{"type":"number"}}}
            }}
        },
        "symbols": {
            "type":"array",
            "items":{
                "type":"object",
                "required":["id","type","label","bbox","port"],
                "properties":{
                    "id":{"type":"string"},
                    "type":{"type":"string"},
                    "label":{"type":"string"},
                    "room_id":{"type":"string"},
                    "bbox":{"type":"object","properties":{
                        "x":{"type":"number"},"y":{"type":"number"},
                        "w":{"type":"number"},"h":{"type":"number"}}},
                    "port":{"type":"object","properties":{"x":{"type":"number"},"y":{"type":"number"}}}
                }
            }
        }
    }
}
