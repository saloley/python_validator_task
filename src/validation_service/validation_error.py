from typing import Dict, Any


class ValidationError:

    def __init__(
        self,
        error_level: str,
        error_text: str,
        file_name: str = "",
        folder_name: str = "",
        line_number: int = 0,
        value_type: str = "",
        value: str = ""
    ):
        self.error_level = error_level
        self.error_text = error_text
        self.file_name = file_name
        self.folder_name = folder_name
        self.line_number = line_number
        self.value_type = value_type
        self.value = value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'error_level': self.error_level,
            'error_text': self.error_text,
            'file_name': self.file_name,
            'folder_name': self.folder_name,
            'line_number': self.line_number,
            'value_type': self.value_type,
            'value': self.value
        }
