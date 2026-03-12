import hashlib


def should_sample(trace_key: str, sample_rate: float) -> bool:
    if sample_rate >= 1.0:
        return True
    if sample_rate <= 0.0:
        return False
    bucket = int(hashlib.sha256(trace_key.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    return bucket <= sample_rate

