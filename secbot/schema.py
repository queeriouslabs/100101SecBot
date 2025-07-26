"""
Schema used in message passing between components and validators used
by the comms module (and others) for asserting the structural correctness of
the messaging.

These schema are not the protocol used by the comms module, all messages
passed in that protocol are validated by these schema.

See the documentation for jsonschema to understand the syntax.
"""
from jsonschema import validate


permission_schema = {
    "$id": "/schemas/permission",

    "type": "object",
    "properties": {
        "perm": {"type": "string"},
        "context": {"type": "object"}
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
        "context": {"type": "object"},
        "code": {"type": "integer"},
        "msg": {"type": "string"}
    },
    "required": ["source_id", "target_id", "code", "msg"]
}


grant_schema = {
    "$id": "/schemas/grant",

    "type": "object",
    "properties": {
        "source_id": {"type": "string"},
        "target_id": {"type": "string"},
        "perm": permission_schema,
        "grant": {"type":  "boolean"},
        "context": {"type": "object"}
    },
    "required": ["perm", "grant"]
}


error_schema = {
    "$id": "/schemas/error",

    "type": "object",
    "properties": {
        "error_code": {"type": "integer"},
        "error_msg": {"type": "string"}
    },
    "required": ["error_code", "error_msg"]
}


event_schema = {
    "$id": "/schemas/event",

    "type": "object",
    "properties": {
        "src_id": {"type": "string"},
        "event": {"type": "string"},
        "context": {"type": "object"}
    },
    "required": ["src_id", "event"]
}


def validate_permission(data):
    validate(data, permission_schema)


def validate_request(data):
    validate(data, request_schema)


def validate_grant(data):
    validate(data, grant_schema)


def validate_response(data):
    validate(data, response_schema)


def validate_error(data):
    validate(data, error_schema)


def validate_event(data):
    validate(data, event_schema)
