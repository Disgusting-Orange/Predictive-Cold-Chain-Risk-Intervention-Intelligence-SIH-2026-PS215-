"""
FrostLink Physics-Informed Synthetic Telemetry Engine -- Label Generator (Phase 16A)
====================================================================================
Computes non-leaking forward early-warning labels strictly derived from future physical trajectories:
  y_next_60_R2 = 1 if max(T_{t+1 ... t+6}) > 4.0°C else 0
"""

import numpy as np
import pandas as pd
from typing import Optional

PROBE_COLS = [
    "Front_Top", "Front_Middle", "Front_Bottom",
    "Middle_Top", "Middle_Middle", "Middle_Bottom",
    "Rear_Top", "Rear_Middle", "Rear_Bottom"
]

class SyntheticLabelGenerator:
    def __init__(
        self,
        excursion_threshold_celsius: float = 4.0,
        warning_threshold_celsius: float = 3.0,
        horizon_steps: int = 6, # 6 steps = 60 minutes
        dt_minutes: float = 10.0
    ):
        self.excursion_threshold = excursion_threshold_celsius
        self.warning_threshold = warning_threshold_celsius
        self.horizon_steps = horizon_steps
        self.dt_minutes = dt_minutes

    def annotate_shipment_labels(self, df_shipment: pd.DataFrame) -> pd.DataFrame:
        """
        Computes forward-looking outcome labels without leaking future states into current features.
        """
        df = df_shipment.copy().sort_values("step_index").reset_index(drop=True)
        n_rows = len(df)
        
        # 1. Compute instantaneous spatial mean at time t
        probe_means = df[PROBE_COLS].mean(axis=1).values
        
        # 2. Instantaneous physical risk state at time t
        # (0 = Safe < 3.0C, 1 = Elevated [3.0, 4.0]C, 2 = Excursion > 4.0C)
        risk_levels = np.zeros(n_rows, dtype=float)
        for i in range(n_rows):
            t_curr = probe_means[i]
            if t_curr > self.excursion_threshold:
                risk_levels[i] = 2.0
            elif t_curr > self.warning_threshold:
                risk_levels[i] = 1.0
            else:
                risk_levels[i] = 0.0
                
        df["risk_level"] = risk_levels
        
        # 3. Forward Early-Warning Target y_next_60_R2
        # Evaluates strictly over future steps: (t+1, t+2, ..., t+horizon)
        y_next_60 = np.full(n_rows, np.nan)
        eta_to_60 = np.full(n_rows, np.nan)
        
        for i in range(n_rows):
            # Check if full 6-step future horizon is available
            if i + self.horizon_steps < n_rows:
                future_slice = probe_means[i + 1 : i + 1 + self.horizon_steps]
                max_future_temp = np.max(future_slice)
                
                if max_future_temp > self.excursion_threshold:
                    y_next_60[i] = 1.0
                    # Calculate time to first excursion breach in minutes
                    breach_indices = np.where(future_slice > self.excursion_threshold)[0]
                    if len(breach_indices) > 0:
                        eta_to_60[i] = float((breach_indices[0] + 1) * self.dt_minutes)
                else:
                    y_next_60[i] = 0.0
            else:
                # Horizon extends beyond end of shipment -> unobservable future
                y_next_60[i] = np.nan
                eta_to_60[i] = np.nan
                
        df["y_next_60_R2"] = y_next_60
        df["eta_to_R2_60"] = eta_to_60
        
        return df
