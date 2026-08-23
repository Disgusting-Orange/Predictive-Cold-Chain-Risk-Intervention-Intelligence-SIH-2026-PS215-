"""
FrostLink Production ML Architecture -- Real-Time Explainability Helper
========================================================================
Accepts an input telemetry feature vector, computes exact SHAP attributions
via TreeExplainer, and formats deterministic human-readable explanations.
"""

import os
import json
import numpy as np
import pandas as pd
import xgboost as xgb
import shap
from typing import Dict, Any, List

class FrostLinkExplainer:
    def __init__(
        self,
        model_path: str = r"ml_pipeline\models\frostlink_xgb_baseline\model.json",
        features_path: str = r"ml_pipeline\models\frostlink_xgb_baseline\features.json",
        metadata_path: str = r"ml_pipeline\explainability\feature_display_metadata.json"
    ):
        with open(features_path, 'r') as f:
            self.feature_names = json.load(f)['features']
            
        with open(metadata_path, 'r') as f:
            self.display_meta = json.load(f)['features']
            
        self.model = xgb.XGBClassifier()
        self.model.load_model(model_path)
        self.explainer = shap.TreeExplainer(self.model)
        self.base_value = float(self.explainer.expected_value) if not isinstance(self.explainer.expected_value, np.ndarray) else float(self.explainer.expected_value[0])

    def explain_instance(self, feature_dict: Dict[str, float], top_k: int = 5) -> Dict[str, Any]:
        """
        Explains an individual prediction vector.
        """
        # Ensure all 40 features exist in exact deterministic order
        row_vector = [feature_dict.get(col, np.nan) for col in self.feature_names]
        df_row = pd.DataFrame([row_vector], columns=self.feature_names)
        
        # Predict probability & margin
        prob = float(self.model.predict_proba(df_row)[0, 1])
        dmat = xgb.DMatrix(df_row)
        margin = float(self.model.get_booster().predict(dmat, output_margin=True)[0])
        
        # Calculate SHAP
        shap_vals = self.explainer.shap_values(df_row)[0]
        
        # Additivity verification (within floating point precision across 150 trees)
        reconstructed = self.base_value + float(np.sum(shap_vals))
        additivity_delta = abs(margin - reconstructed)
        additivity_verified = bool(additivity_delta < 0.02)
        
        contributions = []
        for name, val, s_val in zip(self.feature_names, row_vector, shap_vals):
            meta = self.display_meta.get(name, {})
            contributions.append({
                'feature_name': name,
                'display_name': meta.get('display_name', name),
                'unit': meta.get('unit', ''),
                'observed_value': float(val) if pd.notna(val) else None,
                'shap_value': float(s_val),
                'feature_group': meta.get('feature_group', '')
            })
            
        contrib_df = pd.DataFrame(contributions)
        risk_inc = contrib_df[contrib_df['shap_value'] > 0].sort_values('shap_value', ascending=False).head(top_k).to_dict('records')
        risk_dec = contrib_df[contrib_df['shap_value'] < 0].sort_values('shap_value', ascending=True).head(top_k).to_dict('records')
        
        # Human-readable textual summary
        summary_lines = [
            f"Predicted Excursion Risk: {prob*100:.2f}% (Log-Odds Margin: {margin:.3f})",
            f"Baseline Fleet Prior (Expected Margin): {self.base_value:.3f}",
            "",
            "Top Factors Increasing Predicted Excursion Risk:"
        ]
        for i, item in enumerate(risk_inc, 1):
            val_str = f"{item['observed_value']:.3f} {item['unit']}" if item['observed_value'] is not None else "N/A"
            summary_lines.append(f"  {i}. {item['display_name']} ({item['feature_name']}) = {val_str} -> Model impact: +{item['shap_value']:.4f}")
            
        summary_lines.append("\nTop Factors Reducing Predicted Excursion Risk:")
        for i, item in enumerate(risk_dec, 1):
            val_str = f"{item['observed_value']:.3f} {item['unit']}" if item['observed_value'] is not None else "N/A"
            summary_lines.append(f"  {i}. {item['display_name']} ({item['feature_name']}) = {val_str} -> Model impact: {item['shap_value']:.4f}")
            
        return {
            'predicted_risk_probability': prob,
            'log_odds_margin': margin,
            'base_value_expected_margin': self.base_value,
            'additivity_verified': additivity_verified,
            'additivity_delta': float(additivity_delta),
            'top_risk_increasing_factors': risk_inc,
            'top_risk_reducing_factors': risk_dec,
            'human_readable_explanation': "\n".join(summary_lines)
        }

if __name__ == "__main__":
    explainer = FrostLinkExplainer()
    # Test on a dummy feature dict
    test_dict = {f: 2.0 for f in explainer.feature_names}
    res = explainer.explain_instance(test_dict)
    print("Self-test succeeded! Explanation output sample:")
    print(res['human_readable_explanation'])
