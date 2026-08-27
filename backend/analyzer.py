"""
Data Quality Analysis Engine
Performs comprehensive data profiling and quality scoring.
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime


class DataQualityAnalyzer:
    """Analyzes a DataFrame for data quality issues across multiple dimensions."""

    # Weights for overall quality score
    CATEGORY_WEIGHTS = {
        'completeness': 0.30,
        'uniqueness': 0.20,
        'validity': 0.20,
        'consistency': 0.15,
        'accuracy': 0.15,
    }

    # Severity thresholds (percentage of affected rows)
    SEVERITY_THRESHOLDS = {
        'critical': 20,
        'high': 10,
        'medium': 5,
        'low': 0,
    }

    def __init__(self, df: pd.DataFrame, filename: str = ""):
        self.df = df.copy()
        self.filename = filename
        self.total_rows = len(df)
        self.total_cols = len(df.columns)
        self.total_cells = self.total_rows * self.total_cols
        self.issues = []
        self.column_profiles = {}
        self.category_scores = {}
        self.overall_score = 0

    def run_full_analysis(self) -> dict:
        """Run all analysis modules and return consolidated results."""
        self._profile_columns()
        missing = self._analyze_missing_values()
        duplicates = self._analyze_duplicates()
        dtypes = self._analyze_data_types()
        outliers = self._analyze_outliers()
        invalid = self._analyze_invalid_values()
        consistency = self._analyze_consistency()

        self._calculate_scores(missing, duplicates, outliers, invalid, consistency)

        return {
            'summary': self._get_summary(),
            'column_profiles': self.column_profiles,
            'missing_values': missing,
            'duplicates': duplicates,
            'data_types': dtypes,
            'outliers': outliers,
            'invalid_values': invalid,
            'consistency': consistency,
            'issues': sorted(self.issues, key=lambda x: self._severity_rank(x['severity'])),
            'category_scores': self.category_scores,
            'overall_score': self.overall_score,
        }

    def _severity_rank(self, severity: str) -> int:
        ranks = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        return ranks.get(severity, 4)

    def _classify_severity(self, pct: float) -> str:
        if pct >= self.SEVERITY_THRESHOLDS['critical']:
            return 'critical'
        elif pct >= self.SEVERITY_THRESHOLDS['high']:
            return 'high'
        elif pct >= self.SEVERITY_THRESHOLDS['medium']:
            return 'medium'
        return 'low'

    def _get_summary(self) -> dict:
        total_missing = int(self.df.isnull().sum().sum())
        total_duplicates = int(self.df.duplicated().sum())
        return {
            'filename': self.filename,
            'total_rows': self.total_rows,
            'total_columns': self.total_cols,
            'total_cells': self.total_cells,
            'total_missing': total_missing,
            'missing_percentage': round(total_missing / self.total_cells * 100, 2) if self.total_cells > 0 else 0,
            'total_duplicates': total_duplicates,
            'duplicate_percentage': round(total_duplicates / self.total_rows * 100, 2) if self.total_rows > 0 else 0,
            'total_issues': len(self.issues),
            'memory_usage_mb': round(self.df.memory_usage(deep=True).sum() / (1024 * 1024), 2),
        }

    def _profile_columns(self):
        """Generate detailed profile for each column."""
        for col in self.df.columns:
            series = self.df[col]
            profile = {
                'name': col,
                'dtype': str(series.dtype),
                'inferred_type': self._infer_semantic_type(series),
                'total_count': int(len(series)),
                'missing_count': int(series.isnull().sum()),
                'missing_pct': round(series.isnull().sum() / len(series) * 100, 2) if len(series) > 0 else 0,
                'unique_count': int(series.nunique()),
                'unique_pct': round(series.nunique() / len(series) * 100, 2) if len(series) > 0 else 0,
            }

            non_null = series.dropna()
            if pd.api.types.is_numeric_dtype(series):
                profile.update({
                    'mean': round(float(non_null.mean()), 4) if len(non_null) > 0 else None,
                    'median': round(float(non_null.median()), 4) if len(non_null) > 0 else None,
                    'std': round(float(non_null.std()), 4) if len(non_null) > 1 else None,
                    'min': float(non_null.min()) if len(non_null) > 0 else None,
                    'max': float(non_null.max()) if len(non_null) > 0 else None,
                    'q1': round(float(non_null.quantile(0.25)), 4) if len(non_null) > 0 else None,
                    'q3': round(float(non_null.quantile(0.75)), 4) if len(non_null) > 0 else None,
                    'skewness': round(float(non_null.skew()), 4) if len(non_null) > 2 else None,
                    'zeros_count': int((non_null == 0).sum()),
                    'negative_count': int((non_null < 0).sum()),
                })
            else:
                top_values = non_null.value_counts().head(5)
                profile.update({
                    'top_values': {str(k): int(v) for k, v in top_values.items()},
                    'avg_length': round(float(non_null.astype(str).str.len().mean()), 2) if len(non_null) > 0 else None,
                    'min_length': int(non_null.astype(str).str.len().min()) if len(non_null) > 0 else None,
                    'max_length': int(non_null.astype(str).str.len().max()) if len(non_null) > 0 else None,
                })

            self.column_profiles[col] = profile

    def _infer_semantic_type(self, series: pd.Series) -> str:
        """Infer the semantic type of a column (email, date, phone, etc.)."""
        non_null = series.dropna()
        if len(non_null) == 0:
            return 'empty'

        if pd.api.types.is_numeric_dtype(series):
            if set(non_null.unique()).issubset({0, 1}):
                return 'boolean'
            if series.dtype in ['int64', 'int32']:
                return 'integer'
            return 'float'

        if pd.api.types.is_datetime64_any_dtype(series):
            return 'datetime'

        sample = non_null.astype(str).head(100)

        # Check for date patterns
        date_count = 0
        for val in sample:
            try:
                pd.to_datetime(val)
                date_count += 1
            except (ValueError, TypeError):
                pass
        if date_count > len(sample) * 0.7:
            return 'date_string'

        # Check for email
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        email_match = sample.str.match(email_pattern, na=False).sum()
        if email_match > len(sample) * 0.7:
            return 'email'

        # Check for phone
        phone_pattern = r'^[\+]?[\d\s\-\(\)]{7,15}$'
        phone_match = sample.str.match(phone_pattern, na=False).sum()
        if phone_match > len(sample) * 0.7:
            return 'phone'

        # Check for URL
        url_pattern = r'^https?://'
        url_match = sample.str.match(url_pattern, na=False).sum()
        if url_match > len(sample) * 0.7:
            return 'url'

        # Categorical vs text
        if series.nunique() < min(20, len(series) * 0.05):
            return 'categorical'

        return 'text'

    def _analyze_missing_values(self) -> dict:
        """Analyze missing value patterns across the dataset."""
        result = {'columns': {}, 'total_missing': 0, 'total_pct': 0}

        for col in self.df.columns:
            missing = int(self.df[col].isnull().sum())
            if missing > 0:
                pct = round(missing / self.total_rows * 100, 2)
                result['columns'][col] = {
                    'count': missing,
                    'percentage': pct,
                }
                severity = self._classify_severity(pct)
                self.issues.append({
                    'category': 'completeness',
                    'column': col,
                    'type': 'missing_values',
                    'severity': severity,
                    'description': f"Column '{col}' has {missing} missing values ({pct}%)",
                    'affected_rows': missing,
                    'affected_pct': pct,
                })

        result['total_missing'] = int(self.df.isnull().sum().sum())
        result['total_pct'] = round(result['total_missing'] / self.total_cells * 100, 2) if self.total_cells > 0 else 0
        return result

    def _analyze_duplicates(self) -> dict:
        """Analyze duplicate rows in the dataset."""
        dup_mask = self.df.duplicated(keep='first')
        dup_count = int(dup_mask.sum())
        dup_pct = round(dup_count / self.total_rows * 100, 2) if self.total_rows > 0 else 0

        result = {
            'total_duplicates': dup_count,
            'duplicate_percentage': dup_pct,
            'duplicate_indices': self.df[dup_mask].index.tolist()[:100],  # Cap at 100 for payload size
        }

        if dup_count > 0:
            severity = self._classify_severity(dup_pct)
            self.issues.append({
                'category': 'uniqueness',
                'column': 'ALL',
                'type': 'duplicate_rows',
                'severity': severity,
                'description': f"Dataset has {dup_count} duplicate rows ({dup_pct}%)",
                'affected_rows': dup_count,
                'affected_pct': dup_pct,
            })

        return result

    def _analyze_data_types(self) -> dict:
        """Analyze data type consistency and detect type mismatches."""
        result = {'columns': {}}

        for col in self.df.columns:
            series = self.df[col].dropna()
            if len(series) == 0:
                continue

            col_info = {
                'current_dtype': str(self.df[col].dtype),
                'suggested_dtype': str(self.df[col].dtype),
                'mixed_types': False,
                'convertible_to_numeric': False,
                'convertible_to_datetime': False,
            }

            # Check for mixed types in object columns
            if self.df[col].dtype == 'object':
                types_found = set()
                sample = series.head(500)
                for val in sample:
                    if isinstance(val, str):
                        # Try numeric
                        try:
                            float(val.replace(',', ''))
                            types_found.add('numeric')
                        except (ValueError, AttributeError):
                            types_found.add('string')
                    elif isinstance(val, (int, float)):
                        types_found.add('numeric')
                    else:
                        types_found.add(type(val).__name__)

                col_info['mixed_types'] = len(types_found) > 1
                col_info['types_found'] = list(types_found)

                # Check convertibility
                try:
                    pd.to_numeric(series, errors='raise')
                    col_info['convertible_to_numeric'] = True
                    col_info['suggested_dtype'] = 'numeric'
                except (ValueError, TypeError):
                    pass

                try:
                    pd.to_datetime(series.head(100), errors='raise', infer_datetime_format=True)
                    col_info['convertible_to_datetime'] = True
                    if not col_info['convertible_to_numeric']:
                        col_info['suggested_dtype'] = 'datetime'
                except (ValueError, TypeError):
                    pass

                if col_info['mixed_types']:
                    type_list = ', '.join(col_info.get('types_found', []))
                    self.issues.append({
                        'category': 'validity',
                        'column': col,
                        'type': 'mixed_data_types',
                        'severity': 'high',
                        'description': f"Column '{col}' contains mixed data types: {type_list}",
                        'affected_rows': 0,
                        'affected_pct': 0,
                    })

                if col_info['convertible_to_numeric']:
                    self.issues.append({
                        'category': 'validity',
                        'column': col,
                        'type': 'type_mismatch',
                        'severity': 'medium',
                        'description': f"Column '{col}' is stored as text but contains numeric data",
                        'affected_rows': 0,
                        'affected_pct': 0,
                    })

            result['columns'][col] = col_info

        return result

    def _analyze_outliers(self) -> dict:
        """Detect outliers using IQR and Z-score methods."""
        result = {'columns': {}}

        for col in self.df.columns:
            if not pd.api.types.is_numeric_dtype(self.df[col]):
                continue

            series = self.df[col].dropna()
            if len(series) < 4:
                continue

            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1

            if iqr == 0:
                continue

            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr

            iqr_outliers = series[(series < lower_bound) | (series > upper_bound)]

            # Z-score method
            mean = series.mean()
            standard_deviation = series.std()
            if standard_deviation == 0 or pd.isna(standard_deviation):
                z_scores = np.zeros(len(series))
            else:
                z_scores = np.abs((series.to_numpy() - mean) / standard_deviation)
            z_outliers = series[z_scores > 3]

            outlier_count = len(iqr_outliers)
            outlier_pct = round(outlier_count / len(series) * 100, 2)

            if outlier_count > 0:
                result['columns'][col] = {
                    'iqr_outliers': outlier_count,
                    'z_score_outliers': len(z_outliers),
                    'outlier_pct': outlier_pct,
                    'lower_bound': round(lower_bound, 4),
                    'upper_bound': round(upper_bound, 4),
                    'q1': round(q1, 4),
                    'q3': round(q3, 4),
                    'iqr': round(iqr, 4),
                    'min_outlier': round(float(iqr_outliers.min()), 4) if len(iqr_outliers) > 0 else None,
                    'max_outlier': round(float(iqr_outliers.max()), 4) if len(iqr_outliers) > 0 else None,
                }

                severity = self._classify_severity(outlier_pct)
                self.issues.append({
                    'category': 'accuracy',
                    'column': col,
                    'type': 'outliers',
                    'severity': severity,
                    'description': f"Column '{col}' has {outlier_count} outliers ({outlier_pct}%) outside range [{round(lower_bound, 2)}, {round(upper_bound, 2)}]",
                    'affected_rows': outlier_count,
                    'affected_pct': outlier_pct,
                })

        return result

    def _analyze_invalid_values(self) -> dict:
        """Detect semantically invalid values based on inferred column types."""
        result = {'columns': {}}

        for col in self.df.columns:
            profile = self.column_profiles.get(col, {})
            sem_type = profile.get('inferred_type', 'text')
            series = self.df[col].dropna()
            invalid_details = []

            if sem_type == 'email':
                pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                invalid_mask = ~series.astype(str).str.match(pattern, na=False)
                invalid_count = int(invalid_mask.sum())
                if invalid_count > 0:
                    invalid_details.append({
                        'type': 'invalid_email',
                        'count': invalid_count,
                        'examples': series[invalid_mask].head(5).tolist(),
                    })

            elif sem_type == 'phone':
                pattern = r'^[\+]?[\d\s\-\(\)]{7,15}$'
                invalid_mask = ~series.astype(str).str.match(pattern, na=False)
                invalid_count = int(invalid_mask.sum())
                if invalid_count > 0:
                    invalid_details.append({
                        'type': 'invalid_phone',
                        'count': invalid_count,
                        'examples': series[invalid_mask].head(5).tolist(),
                    })

            elif sem_type in ('integer', 'float'):
                # Check for negative values in columns that likely shouldn't have them
                col_lower = col.lower()
                non_negative_hints = ['age', 'price', 'cost', 'amount', 'quantity', 'count',
                                      'salary', 'revenue', 'weight', 'height', 'distance']
                if any(hint in col_lower for hint in non_negative_hints):
                    neg_count = int((series < 0).sum())
                    if neg_count > 0:
                        invalid_details.append({
                            'type': 'negative_values',
                            'count': neg_count,
                            'examples': series[series < 0].head(5).tolist(),
                        })

                # Check for unreasonable age values
                if 'age' in col_lower:
                    unreasonable = series[(series < 0) | (series > 150)]
                    if len(unreasonable) > 0:
                        invalid_details.append({
                            'type': 'unreasonable_age',
                            'count': len(unreasonable),
                            'examples': unreasonable.head(5).tolist(),
                        })

            elif sem_type == 'date_string':
                invalid_count = 0
                for val in series.head(500):
                    try:
                        parsed = pd.to_datetime(val)
                        if parsed > datetime.now():
                            invalid_count += 1
                    except (ValueError, TypeError):
                        invalid_count += 1
                if invalid_count > 0:
                    invalid_details.append({
                        'type': 'invalid_date',
                        'count': invalid_count,
                        'examples': [],
                    })

            # Whitespace-only values
            if self.df[col].dtype == 'object':
                ws_mask = series.astype(str).str.strip().eq('')
                ws_count = int(ws_mask.sum())
                if ws_count > 0:
                    invalid_details.append({
                        'type': 'whitespace_only',
                        'count': ws_count,
                        'examples': [],
                    })

            if invalid_details:
                total_invalid = sum(d['count'] for d in invalid_details)
                pct = round(total_invalid / len(series) * 100, 2) if len(series) > 0 else 0
                result['columns'][col] = {
                    'total_invalid': total_invalid,
                    'invalid_pct': pct,
                    'details': invalid_details,
                }
                severity = self._classify_severity(pct)
                for detail in invalid_details:
                    self.issues.append({
                        'category': 'validity',
                        'column': col,
                        'type': detail['type'],
                        'severity': severity,
                        'description': f"Column '{col}' has {detail['count']} {detail['type'].replace('_', ' ')} values",
                        'affected_rows': detail['count'],
                        'affected_pct': round(detail['count'] / len(series) * 100, 2) if len(series) > 0 else 0,
                    })

        return result

    def _analyze_consistency(self) -> dict:
        """Analyze data consistency: case issues, whitespace, format variations."""
        result = {'columns': {}}

        for col in self.df.columns:
            if self.df[col].dtype != 'object':
                continue

            series = self.df[col].dropna().astype(str)
            if len(series) == 0:
                continue

            issues_found = {}

            # Case inconsistencies
            lower_values = series.str.lower()
            unique_lower = lower_values.nunique()
            unique_original = series.nunique()
            if unique_original > unique_lower:
                diff = unique_original - unique_lower
                issues_found['case_inconsistency'] = {
                    'count': diff,
                    'description': f"{diff} values differ only by case",
                    'examples': self._find_case_examples(series),
                }

            # Leading/trailing whitespace
            stripped = series.str.strip()
            ws_issues = (series != stripped).sum()
            if ws_issues > 0:
                issues_found['whitespace_issues'] = {
                    'count': int(ws_issues),
                    'description': f"{ws_issues} values have leading/trailing whitespace",
                }

            # Extra internal whitespace
            normalized = series.str.replace(r'\s+', ' ', regex=True)
            extra_ws = (series != normalized).sum()
            if extra_ws > 0:
                issues_found['extra_whitespace'] = {
                    'count': int(extra_ws),
                    'description': f"{extra_ws} values have extra internal whitespace",
                }

            if issues_found:
                total_issues = sum(v['count'] for v in issues_found.values())
                pct = round(total_issues / len(series) * 100, 2)
                result['columns'][col] = {
                    'issues': issues_found,
                    'total_issues': total_issues,
                    'issue_pct': pct,
                }
                severity = self._classify_severity(pct)
                for issue_type, info in issues_found.items():
                    self.issues.append({
                        'category': 'consistency',
                        'column': col,
                        'type': issue_type,
                        'severity': severity,
                        'description': f"Column '{col}': {info['description']}",
                        'affected_rows': info['count'],
                        'affected_pct': round(info['count'] / len(series) * 100, 2),
                    })

        return result

    def _find_case_examples(self, series: pd.Series) -> list:
        """Find examples of case inconsistency."""
        examples = []
        lower_groups = series.str.lower().value_counts()
        for val in lower_groups.index:
            variants = series[series.str.lower() == val].unique()
            if len(variants) > 1:
                examples.append(list(variants[:3]))
                if len(examples) >= 3:
                    break
        return examples

    def _calculate_scores(self, missing, duplicates, outliers, invalid, consistency):
        """Calculate category-wise and overall quality scores."""
        # Completeness: based on missing values
        missing_pct = missing['total_pct']
        self.category_scores['completeness'] = max(0, round(100 - missing_pct * 2, 1))

        # Uniqueness: based on duplicate rows
        dup_pct = duplicates['duplicate_percentage']
        self.category_scores['uniqueness'] = max(0, round(100 - dup_pct * 3, 1))

        # Validity: based on invalid values and type mismatches
        validity_issues = [i for i in self.issues if i['category'] == 'validity']
        validity_penalty = sum(min(i['affected_pct'], 30) for i in validity_issues)
        self.category_scores['validity'] = max(0, round(100 - validity_penalty, 1))

        # Consistency: based on consistency issues
        consistency_issues = [i for i in self.issues if i['category'] == 'consistency']
        consistency_penalty = sum(min(i['affected_pct'], 20) for i in consistency_issues)
        self.category_scores['consistency'] = max(0, round(100 - consistency_penalty, 1))

        # Accuracy: based on outliers
        accuracy_issues = [i for i in self.issues if i['category'] == 'accuracy']
        accuracy_penalty = sum(min(i['affected_pct'], 25) for i in accuracy_issues)
        self.category_scores['accuracy'] = max(0, round(100 - accuracy_penalty, 1))

        # Overall weighted score
        self.overall_score = round(sum(
            self.category_scores[cat] * weight
            for cat, weight in self.CATEGORY_WEIGHTS.items()
        ), 1)
