import json
import enum


class Variables:
    class ValueType(enum.Enum):

        BOOLEAN = "boolean"
        DATE = "date"
        FILE = "file"
        FLOAT = "float"
        INTEGER = "integer"
        JSON = "json"
        LONG = "long"
        SHORT = "short"
        STRING = "string"
        XML = "XML"

        @classmethod
        def is_valid(cls, value):
            return any(value == item.value for item in cls)

    def __init__(self, variables={}):
        self.variables = {}
        for k, v in variables.items():
            if not isinstance(v, dict) or "value" not in v:
                self.variables[k] = {"value": v}
            else:
                self.variables[k] = v

    def __getitem__(self, key):
        return self.get_variable(key)

    def __setitem__(self, key, value):
        self.set_variable(key, value)

    def get_variable(self, variable_name):
        variable = self.variables.get(variable_name, None)
        if not variable:
            return None
        return variable["value"]

    def set_variable(self, name, value, value_type=None):
        # value_type could be integer, long, string, boolean, json
        data = {"value": value}
        if self.ValueType.is_valid(value_type):
            if value_type == self.ValueType.JSON:
                data["value"] = json.dumps(value)
            data["type"] = value_type
            data["valueInfo"] = {}
        self.variables[name] = data
