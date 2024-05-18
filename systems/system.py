class System:
    def setup(self):
        return NotImplementedError(f"Child system MUST implement {self.setup.__name__}")

    def process_entities(self):
        return NotImplementedError(f"Child system MUST implement {self.process_entities.__name__}")
