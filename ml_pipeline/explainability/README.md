# FrostLink ML Pipeline -- Explainability Architecture (SHAP)

## Overview
This package provides post-hoc game-theoretic explainability (SHAP TreeExplainer) for the production FrostLink XGBoost early-warning baseline model.

---

## Directory Structure
```
ml_pipeline/explainability/
├── shap_explainer.py            # Global & local SHAP computation engine
├── explain_prediction.py        # Real-time instance explanation helper
├── feature_display_metadata.json# Human-readable feature metadata and units
├── global_feature_importance.csv# Global mean absolute SHAP ranking
├── local_explanations.json      # Detailed TP, TN, FP, FN explanations
├── shap_summary_bar.png         # Top-20 global feature importance bar plot
├── shap_beeswarm.png            # Top-20 feature directional impact plot
├── test_shap_pipeline.py        # 10-point explainability validation suite
├── validation_test_report.json  # Test execution report
└── README.md                    # Explainability documentation
```

---

## Key Findings
1. **Dominant Global Drivers:**
   - `v4_p95_t` (Instantaneous 95th Percentile Probe Temperature): Global Mean $|SHAP| = 1.043$
   - `W60_spatial_range_max` (60m Peak Spatial Spread): Global Mean $|SHAP| = 0.559$
   - `W60_spatial_range_mean` (60m Average Spatial Range): Global Mean $|SHAP| = 0.268$
   - `W60_T_max` (60m Trailing Maximum Temperature): Global Mean $|SHAP| = 0.263$
   - `v4_slope_long_t` (Long-Term Warming Slope): Global Mean $|SHAP| = 0.183$
2. **False Positive Driver:** Local probe spikes (`hot_ratio_t > 0`, `v4_p95_t > 4.0°C`) trigger high model risk even when container-average temperature remains moderate.
3. **False Negative Driver:** Excursions beginning from very cold baseline cargo temperatures ($T \approx 1.5^\circ\text{C}$) are suppressed by the model because low 95th percentile probe levels dominate the tree paths.
