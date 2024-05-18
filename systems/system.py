class System:
    def setup(self):
        return NotImplementedError(f"Child system MUST implement {self.setup.__name__}")

    def run(self):
        return NotImplementedError(f"Child system MUST implement {self.run.__name__}")
