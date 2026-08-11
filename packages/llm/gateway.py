class LlmGateway:
    def generate_structured(self, *, task: str, context: dict, output_schema: dict | None = None) -> dict:
        raise NotImplementedError
