"""Factor cleanup and orthogonalization pipeline."""

import pandas as pd
import numpy as np
from typing import List, Dict
import quant_core

class FactorCleaner:
    """Cleans up redundant factors and performs orthogonalization."""

    def __init__(self, correlation_threshold: float = 0.95):
        self.threshold = correlation_threshold

    def get_redundant_factors(self, factor_matrix: pd.DataFrame) -> List[str]:
        """Identify factors with correlation > threshold."""
        corr_matrix = factor_matrix.corr().abs()
        redundant = set()
        
        for i in range(len(corr_matrix.columns)):
            for j in range(i + 1, len(corr_matrix.columns)):
                if corr_matrix.iloc[i, j] > self.threshold:
                    col_name = corr_matrix.columns[j]
                    redundant.add(col_name)
                    
        return list(redundant)

    def orthogonalize(self, factor_matrix: pd.DataFrame) -> pd.DataFrame:
        """Apply Rust-based orthogonalization."""
        # Convert df to List[List[f64]]
        matrix_data = factor_matrix.T.values.tolist()
        
        # Call Rust implementation
        ortho_data = quant_core.fast_orthogonalize(matrix_data)
        
        # Reconstruct DataFrame
        return pd.DataFrame(
            np.array(ortho_data).T, 
            index=factor_matrix.index, 
            columns=factor_matrix.columns
        )
