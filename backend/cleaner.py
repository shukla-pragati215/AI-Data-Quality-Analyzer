"""
Dataset Cleaning Engine
Applies cleaning operations without modifying the original dataset.
"""

import pandas as pd
import numpy as np
from scipy import stats


class DataCleaner:
    """Applies cleaning operations to a copy of the dataset."""

    def __init__(self, df: pd.DataFrame):
        self.original_df = df.copy()
        self.cleaned_df = df.copy()
        self.operations_log = []

    def apply_operations(self, operations: list) -> dict:
        """
        Apply a list of cleaning operations.

        Each operation is a dict with:
          - type: 'fill_missing', 'remove_duplicates', 'handle_outliers',
                  'fix_data_types', 'standardize_values'
          - params: operation-specific parameters
        """
        for op in operations:
            op_type = op.get('type')
            params = op.get('params', {})

            if op_type == 'fill_missing':
                self._fill_missing(params)
            elif op_type == 'remove_duplicates':
                self._remove_duplicates(params)
            elif op_type == 'handle_outliers':
                self._handle_outliers(params)
            elif op_type == 'fix_data_types':
                self._fix_data_types(params)
            elif op_type == 'standardize_values':
                self._standardize_values(params)

        return {
            'cleaned_rows': len(self.cleaned_df),
            'cleaned_columns': len(self.cleaned_df.columns),
            'original_rows': len(self.original_df),
            'original_columns': len(self.original_df.columns),
            'operations_applied': self.operations_log,
            'rows_removed': len(self.original_df) - len(self.cleaned_df),
            'cells_modified': self._count_differences(),
        }

    def _fill_missing(self, params: dict):
        """Fill missing values using specified strategy."""
        columns = params.get('columns', [])
        strategy = params.get('strategy', 'auto')
        fill_value = params.get('fill_value', None)

        if not columns:
            columns = self.cleaned_df.columns[self.cleaned_df.isnull().any()].tolist()

        for col in columns:
            if col not in self.cleaned_df.columns:
                continue

            missing_before = int(self.cleaned_df[col].isnull().sum())
            if missing_before == 0:
                continue

            if strategy == 'auto':
                if pd.api.types.is_numeric_dtype(self.cleaned_df[col]):
                    # Use median for skewed data, mean for normal
                    non_null = self.cleaned_df[col].dropna()
                    if len(non_null) > 2:
                        skewness = abs(non_null.skew())
                        if skewness > 1:
                            self.cleaned_df[col].fillna(self.cleaned_df[col].median(), inplace=True)
                            used_strategy = 'median (auto - skewed distribution)'
                        else:
                            self.cleaned_df[col].fillna(round(self.cleaned_df[col].mean(), 4), inplace=True)
                            used_strategy = 'mean (auto - normal distribution)'
                    else:
                        self.cleaned_df[col].fillna(0, inplace=True)
                        used_strategy = 'zero (auto - insufficient data)'
                else:
                    mode_val = self.cleaned_df[col].mode()
                    if len(mode_val) > 0:
                        self.cleaned_df[col].fillna(mode_val[0], inplace=True)
                        used_strategy = f'mode: {mode_val[0]}'
                    else:
                        self.cleaned_df[col].fillna('Unknown', inplace=True)
                        used_strategy = 'constant: Unknown'
            elif strategy == 'mean':
                self.cleaned_df[col].fillna(round(self.cleaned_df[col].mean(), 4), inplace=True)
                used_strategy = 'mean'
            elif strategy == 'median':
                self.cleaned_df[col].fillna(self.cleaned_df[col].median(), inplace=True)
                used_strategy = 'median'
            elif strategy == 'mode':
                mode_val = self.cleaned_df[col].mode()
                if len(mode_val) > 0:
                    self.cleaned_df[col].fillna(mode_val[0], inplace=True)
                used_strategy = 'mode'
            elif strategy == 'constant':
                self.cleaned_df[col].fillna(fill_value if fill_value is not None else 0, inplace=True)
                used_strategy = f'constant: {fill_value}'
            elif strategy == 'forward_fill':
                self.cleaned_df[col].fillna(method='ffill', inplace=True)
                used_strategy = 'forward fill'
            elif strategy == 'backward_fill':
                self.cleaned_df[col].fillna(method='bfill', inplace=True)
                used_strategy = 'backward fill'
            else:
                continue

            missing_after = int(self.cleaned_df[col].isnull().sum())
            self.operations_log.append({
                'type': 'fill_missing',
                'column': col,
                'strategy': used_strategy,
                'filled_count': missing_before - missing_after,
            })

    def _remove_duplicates(self, params: dict):
        """Remove duplicate rows."""
        keep = params.get('keep', 'first')
        subset = params.get('subset', None)

        rows_before = len(self.cleaned_df)
        self.cleaned_df.drop_duplicates(keep=keep, subset=subset, inplace=True)
        self.cleaned_df.reset_index(drop=True, inplace=True)
        rows_removed = rows_before - len(self.cleaned_df)

        self.operations_log.append({
            'type': 'remove_duplicates',
            'column': 'ALL',
            'strategy': f'keep={keep}',
            'rows_removed': rows_removed,
        })

    def _handle_outliers(self, params: dict):
        """Handle outliers using IQR method - cap or remove."""
        columns = params.get('columns', [])
        method = params.get('method', 'cap')  # 'cap' or 'remove'

        if not columns:
            columns = self.cleaned_df.select_dtypes(include=[np.number]).columns.tolist()

        for col in columns:
            if col not in self.cleaned_df.columns:
                continue
            if not pd.api.types.is_numeric_dtype(self.cleaned_df[col]):
                continue

            series = self.cleaned_df[col].dropna()
            if len(series) < 4:
                continue

            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            outlier_mask = (self.cleaned_df[col] < lower_bound) | (self.cleaned_df[col] > upper_bound)
            outlier_count = int(outlier_mask.sum())

            if outlier_count == 0:
                continue

            if method == 'cap':
                self.cleaned_df.loc[self.cleaned_df[col] < lower_bound, col] = lower_bound
                self.cleaned_df.loc[self.cleaned_df[col] > upper_bound, col] = upper_bound
                self.operations_log.append({
                    'type': 'handle_outliers',
                    'column': col,
                    'strategy': f'capped to [{round(lower_bound, 2)}, {round(upper_bound, 2)}]',
                    'affected_count': outlier_count,
                })
            elif method == 'remove':
                self.cleaned_df = self.cleaned_df[~outlier_mask]
                self.cleaned_df.reset_index(drop=True, inplace=True)
                self.operations_log.append({
                    'type': 'handle_outliers',
                    'column': col,
                    'strategy': 'removed outlier rows',
                    'rows_removed': outlier_count,
                })

    def _fix_data_types(self, params: dict):
        """Convert columns to their correct data types."""
        columns = params.get('columns', [])

        if not columns:
            # Auto-detect convertible columns
            for col in self.cleaned_df.columns:
                if self.cleaned_df[col].dtype == 'object':
                    columns.append(col)

        for col in columns:
            if col not in self.cleaned_df.columns:
                continue
            if self.cleaned_df[col].dtype != 'object':
                continue

            series = self.cleaned_df[col].dropna()
            if len(series) == 0:
                continue

            # Try numeric conversion
            try:
                converted = pd.to_numeric(self.cleaned_df[col], errors='coerce')
                non_null_orig = self.cleaned_df[col].notna().sum()
                non_null_conv = converted.notna().sum()
                # Only convert if we don't lose too many values
                if non_null_conv >= non_null_orig * 0.9:
                    self.cleaned_df[col] = converted
                    self.operations_log.append({
                        'type': 'fix_data_types',
                        'column': col,
                        'strategy': f'converted from text to numeric',
                        'original_type': 'object',
                        'new_type': str(converted.dtype),
                    })
                    continue
            except (ValueError, TypeError):
                pass

            # Try datetime conversion
            try:
                converted = pd.to_datetime(self.cleaned_df[col], errors='coerce', infer_datetime_format=True)
                non_null_orig = self.cleaned_df[col].notna().sum()
                non_null_conv = converted.notna().sum()
                if non_null_conv >= non_null_orig * 0.8:
                    self.cleaned_df[col] = converted
                    self.operations_log.append({
                        'type': 'fix_data_types',
                        'column': col,
                        'strategy': 'converted from text to datetime',
                        'original_type': 'object',
                        'new_type': 'datetime64',
                    })
            except (ValueError, TypeError):
                pass

    def _standardize_values(self, params: dict):
        """Standardize string values: trim whitespace, normalize case, etc."""
        columns = params.get('columns', [])
        normalize_case = params.get('normalize_case', True)
        trim_whitespace = params.get('trim_whitespace', True)
        normalize_whitespace = params.get('normalize_whitespace', True)

        if not columns:
            columns = self.cleaned_df.select_dtypes(include=['object']).columns.tolist()

        for col in columns:
            if col not in self.cleaned_df.columns:
                continue
            if self.cleaned_df[col].dtype != 'object':
                continue

            changes = 0
            original = self.cleaned_df[col].copy()

            if trim_whitespace:
                self.cleaned_df[col] = self.cleaned_df[col].apply(
                    lambda x: x.strip() if isinstance(x, str) else x
                )

            if normalize_whitespace:
                self.cleaned_df[col] = self.cleaned_df[col].apply(
                    lambda x: ' '.join(x.split()) if isinstance(x, str) else x
                )

            if normalize_case:
                # Title case for name-like columns, lower for others
                col_lower = col.lower()
                name_hints = ['name', 'city', 'state', 'country', 'title']
                if any(hint in col_lower for hint in name_hints):
                    self.cleaned_df[col] = self.cleaned_df[col].apply(
                        lambda x: x.title() if isinstance(x, str) else x
                    )
                    case_strategy = 'title case'
                else:
                    self.cleaned_df[col] = self.cleaned_df[col].apply(
                        lambda x: x.strip() if isinstance(x, str) else x
                    )
                    case_strategy = 'trimmed'

            changes = int((original != self.cleaned_df[col]).sum())
            if changes > 0:
                self.operations_log.append({
                    'type': 'standardize_values',
                    'column': col,
                    'strategy': f'standardized ({case_strategy if normalize_case else "whitespace only"})',
                    'affected_count': changes,
                })

    def _count_differences(self) -> int:
        """Count the number of cells that differ between original and cleaned."""
        try:
            if len(self.original_df) != len(self.cleaned_df):
                return -1  # Row count changed

            common_cols = [c for c in self.original_df.columns if c in self.cleaned_df.columns]
            diff_count = 0
            for col in common_cols:
                orig = self.original_df[col].reset_index(drop=True)
                clean = self.cleaned_df[col].reset_index(drop=True)
                min_len = min(len(orig), len(clean))
                orig = orig.iloc[:min_len]
                clean = clean.iloc[:min_len]
                diff_count += int((orig.fillna('__NULL__').astype(str) != clean.fillna('__NULL__').astype(str)).sum())
            return diff_count
        except Exception:
            return -1

    def get_cleaned_dataframe(self) -> pd.DataFrame:
        """Return the cleaned DataFrame."""
        return self.cleaned_df.copy()

    def get_preview(self, n_rows: int = 20) -> dict:
        """Return preview data for both original and cleaned datasets."""
        def df_to_preview(df, n):
            return {
                'columns': df.columns.tolist(),
                'rows': df.head(n).fillna('').astype(str).values.tolist(),
                'total_rows': len(df),
                'total_columns': len(df.columns),
            }

        return {
            'original': df_to_preview(self.original_df, n_rows),
            'cleaned': df_to_preview(self.cleaned_df, n_rows),
        }
