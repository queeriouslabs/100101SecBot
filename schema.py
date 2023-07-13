from jsonschema import validate


permission_schema = {
    "$id": "/schemas/permission",

    "type": "object",
    "properties": {
        "perm": {"type": "string"},
        "context" : {"type": "object"}
    },
    "required": ["perm"]
}


request_schema = {
    "$id": "/schemas/request",

    "type": "object",
    "properties": {
        "source_id": {"type": "string"},
        "target_id": {"type": "string"},
        "permissions": {
            "type": "array",
            # "items": { "$ref": "/schemas/permission" },
            "items": permission_schema,
            "minContains": 1,
        }
    },
    "required": ["source_id", "target_id", "permissions"]
}

response_schema = {
    "$id": "/schemas/response",

    "type": "object",
    "properties": {
        "source_id": {"type": "string"},
        "target_id": {"type": "string"},
        "perm": permission_schema,
        "grant": {"type":  "boolean"},
        "context" : {"type": "object"}
    },
    "required": ["perm", "grant"]
}


error_schema = {
    "$id": "/schemas/error",

    "type": "object",
    "properties": {
        "error_code": {"type": "int"},
        "error_msg": {"type": "string"}
    },
    "required": ["error_code", "error_msg"]
}


def validate_permission(data):
    validate(data, permission_schema)

def validate_request(data):
    validate(data, request_schema)

def validate_response(data):
    validate(data, response_schema)

def validate_error(data):
    validate(data, error_schema)
