import importlib.util
import json
import os
from typing import Dict
from pydantic import BaseModel, ValidationError

from constants.message_types import MessageTypes


class MessageDecoder:
    def __init__(self):
        self._MESSAGE_MODELS = self._import_schema_models()

    def decode_message(self, data: str) -> BaseModel:
        """
        Function to decode a string into a Pydantic model based on message type
        """
        # Check if the input data is a string
        if not isinstance(data, str):
            raise ValueError("Input data must be a string")

        # Try parsing the string into a dictionary
        try:
            parsed_data = json.loads(data)
        except Exception as e:
            print("Error parsing JSON:", e)
            raise ValueError("Invalid input data format")

        # Check if parsed_data is a dictionary
        if not isinstance(parsed_data, dict):
            raise ValueError("Parsed data is not a dictionary")

        # Get the message type
        message_type = parsed_data.get("type")
        if not message_type:
            raise ValueError("Message type is missing")

        # Get the corresponding model based on message type
        message_model = self._MESSAGE_MODELS.get(message_type)
        if not message_model:
            raise ValueError(f"No matching message schema found for type '{message_type}'")

        # Try parsing the parsed dictionary into the selected Pydantic model
        try:
            return message_model.model_validate(parsed_data)
        except ValidationError as e:
            print("Validation error:", e)
            raise ValueError(f"Validation error for message type '{message_type}': {e}")

    def _import_schema_models(self) -> Dict[MessageTypes, BaseModel]:
        """
        Function to dynamically import all Pydantic models from the schemas directory
        """
        message_models = dict()

        directory = "schemas"

        # Get a list of all Python files in the directory
        files = [f[:-3] for f in os.listdir(directory) if f.endswith('.py') and not f.startswith('__')]

        # Import all Pydantic models from the files
        for file in files:
            module_name = f'schemas.{file}'
            module = importlib.import_module(module_name)

            # Get all classes defined in the module
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, type) and issubclass(obj, BaseModel) and obj != BaseModel:
                    # Ensure the model has a 'type' attribute for message type
                    if "type" in obj.model_fields:
                        message_models[obj.model_fields['type'].default] = obj

        return message_models
