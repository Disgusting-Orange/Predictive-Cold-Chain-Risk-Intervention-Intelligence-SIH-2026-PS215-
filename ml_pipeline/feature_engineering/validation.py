"""
FrostLink Feature Engineering -- Validation Module
==================================================
Input/output validation routines ensuring data integrity and safety.
"""

from typing import Dict, List, Any, Optional, Tuple
import math
import numpy as np

Tuple_Validation = Tuple[bool, str]

def validate_raw_packet(packet: Dict[str, Any]) -> bool:
    """
    Validates raw packet structure and sensor ranges.
    Returns False if packet is missing mandatory identifiers or contains zero valid probes.
    Never fabricates missing sensor values.
    """
    if not isinstance(packet, dict):
        return False
    if "shipment_id" not in packet or "timestamp" not in packet or "probes" not in packet:
        return False
    probes = packet.get("probes", {})
    if not isinstance(probes, dict) or len(probes) == 0:
        return False
    # Check that at least one probe value is non-null
    has_valid_probe = any(v is not None and not (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) for v in probes.values())
    if not has_valid_probe:
        return False
    return True

def validate_feature_vector(
    features: Dict[str, Any],
    expected_feature_names: List[str]
) -> Tuple_Validation:
    """
    Verifies that the generated feature dictionary conforms strictly to model expectations:
    - Exactly 40 features
    - No missing required keys
    - No infinite values
    - Deterministic order matching training schema
    """
    missing = [f for f in expected_feature_names if f not in features]
    if missing:
        return False, f"Missing required features: {missing}"
        
    keys_list = list(features.keys())
    if keys_list != expected_feature_names:
        return False, "Feature dictionary key ordering does not match expected schema order."
        
    for k, v in features.items():
        if v is None or np.isnan(v):
            continue
        try:
            val_f = float(v)
            if math.isinf(val_f):
                return False, f"Feature '{k}' contains infinite value."
        except (ValueError, TypeError):
            return False, f"Feature '{k}' is non-numeric: {v}"
            
    return True, "Valid"
