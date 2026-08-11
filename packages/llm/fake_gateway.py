class FakeLlmGateway:
    def generate_structured(self, *, task: str, context: dict, output_schema: dict | None = None) -> dict:
        if task == "impact-analysis":
            return {
                "impacted_modules": [
                    {"name": "refund-service", "reason": "Refund retry touches refund flow.", "severity": "medium"}
                ],
                "impacted_apis": [],
                "risks": [
                    {"risk": "Retry may violate idempotency.", "severity": "high", "mitigation": "Cap retries and check idempotency keys."}
                ],
                "test_suggestions": ["Retry succeeds after transient failure.", "Retry stops after max attempts."],
            }
        if task == "test-case-generation":
            return {"test_suggestions": ["Generate regression tests for impacted modules."]}
        if task == "risk-check":
            return {"risks": [{"risk": "Review high-risk module changes.", "severity": "medium"}]}
        return {"summary": context.get("summary", "")}
