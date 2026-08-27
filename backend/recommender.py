"""
AI Recommendation Engine
Generates context-aware, issue-specific recommendations based on detected data quality problems.
"""


class AIRecommender:
    """Rule-based AI recommendation engine that analyzes detected issues
    and provides actionable, context-specific suggestions."""

    def __init__(self, analysis_results: dict):
        self.results = analysis_results
        self.issues = analysis_results.get('issues', [])
        self.column_profiles = analysis_results.get('column_profiles', {})
        self.summary = analysis_results.get('summary', {})
        self.category_scores = analysis_results.get('category_scores', {})
        self.recommendations = []

    def generate_recommendations(self) -> list:
        """Generate all recommendations based on detected issues."""
        self._recommend_missing_values()
        self._recommend_duplicates()
        self._recommend_data_types()
        self._recommend_outliers()
        self._recommend_invalid_values()
        self._recommend_consistency()
        self._recommend_overall()

        # Sort by priority
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        self.recommendations.sort(key=lambda x: priority_order.get(x.get('priority', 'low'), 4))

        return self.recommendations

    def _recommend_missing_values(self):
        """Generate recommendations for missing value issues."""
        missing_issues = [i for i in self.issues if i['type'] == 'missing_values']
        if not missing_issues:
            return

        for issue in missing_issues:
            col = issue['column']
            pct = issue['affected_pct']
            profile = self.column_profiles.get(col, {})
            inferred_type = profile.get('inferred_type', 'unknown')

            if pct > 50:
                explanation = (
                    f"Column '{col}' has {pct}% missing values — more than half the data is absent. "
                    f"This level of missingness severely compromises any analysis or model using this column."
                )
                action = (
                    f"Consider dropping column '{col}' entirely if it's not critical to your analysis. "
                    f"If the column is essential, investigate why so much data is missing (data collection issue?) "
                    f"and consider whether imputation is appropriate given the high missingness rate."
                )
                priority = 'critical'
            elif pct > 20:
                explanation = (
                    f"Column '{col}' has {pct}% missing values. This significant gap may introduce bias "
                    f"if the missingness is not random (e.g., certain categories are systematically absent)."
                )
                if inferred_type in ('integer', 'float'):
                    skewness = profile.get('skewness')
                    if skewness and abs(skewness) > 1:
                        action = (
                            f"Use median imputation for '{col}' since the distribution is skewed "
                            f"(skewness: {skewness}). Mean imputation would be biased by extreme values. "
                            f"Consider also using multiple imputation if this column is used in statistical modeling."
                        )
                    else:
                        action = (
                            f"Use mean imputation for '{col}' as the distribution appears approximately normal. "
                            f"Alternatively, use regression imputation to preserve relationships with other variables."
                        )
                else:
                    action = (
                        f"Use mode imputation (most frequent value) for '{col}'. "
                        f"If the column has many categories, consider grouping rare categories first."
                    )
                priority = 'high'
            elif pct > 5:
                explanation = (
                    f"Column '{col}' has {pct}% missing values. While moderate, these gaps should be "
                    f"addressed to ensure data quality."
                )
                if inferred_type in ('integer', 'float'):
                    action = (
                        f"Fill missing values in '{col}' with the median (robust to outliers) or mean. "
                        f"The auto-fill feature will choose the best strategy based on the distribution."
                    )
                else:
                    action = (
                        f"Fill missing values in '{col}' with the most frequent value (mode). "
                        f"Use the auto-fill feature for automatic strategy selection."
                    )
                priority = 'medium'
            else:
                explanation = (
                    f"Column '{col}' has {pct}% missing values — a small amount that's unlikely to "
                    f"significantly impact analysis."
                )
                action = (
                    f"Apply auto-fill to handle the small number of missing values in '{col}'. "
                    f"The system will select the appropriate strategy based on data type and distribution."
                )
                priority = 'low'

            self.recommendations.append({
                'id': f'missing_{col}',
                'category': 'Missing Values',
                'priority': priority,
                'column': col,
                'title': f"Missing values in '{col}' ({pct}%)",
                'explanation': explanation,
                'action': action,
                'auto_fixable': True,
                'fix_operation': {
                    'type': 'fill_missing',
                    'params': {'columns': [col], 'strategy': 'auto'},
                },
            })

    def _recommend_duplicates(self):
        """Generate recommendations for duplicate row issues."""
        dup_issues = [i for i in self.issues if i['type'] == 'duplicate_rows']
        if not dup_issues:
            return

        for issue in dup_issues:
            count = issue['affected_rows']
            pct = issue['affected_pct']

            if pct > 20:
                explanation = (
                    f"The dataset contains {count} exact duplicate rows ({pct}% of all rows). "
                    f"This is a significant data quality issue that will inflate counts, skew distributions, "
                    f"and bias any analysis. Common causes include duplicate data imports or ETL pipeline errors."
                )
                priority = 'critical'
            elif pct > 5:
                explanation = (
                    f"Found {count} duplicate rows ({pct}% of the dataset). Duplicates can distort "
                    f"statistical analyses, artificially inflate frequency counts, and lead to overfitting in models."
                )
                priority = 'high'
            else:
                explanation = (
                    f"Found {count} duplicate rows ({pct}%). A small number of duplicates that should "
                    f"still be reviewed and cleaned."
                )
                priority = 'medium'

            self.recommendations.append({
                'id': 'duplicate_rows',
                'category': 'Duplicates',
                'priority': priority,
                'column': 'ALL',
                'title': f"{count} duplicate rows detected ({pct}%)",
                'explanation': explanation,
                'action': (
                    f"Remove the {count} duplicate rows, keeping the first occurrence of each. "
                    f"Before removing, verify that these are truly unwanted duplicates and not "
                    f"legitimate repeated observations (e.g., time-series data)."
                ),
                'auto_fixable': True,
                'fix_operation': {
                    'type': 'remove_duplicates',
                    'params': {'keep': 'first'},
                },
            })

    def _recommend_data_types(self):
        """Generate recommendations for data type issues."""
        type_issues = [i for i in self.issues if i['type'] in ('mixed_data_types', 'type_mismatch')]

        for issue in type_issues:
            col = issue['column']

            if issue['type'] == 'mixed_data_types':
                self.recommendations.append({
                    'id': f'mixed_types_{col}',
                    'category': 'Data Types',
                    'priority': 'high',
                    'column': col,
                    'title': f"Mixed data types in '{col}'",
                    'explanation': (
                        f"Column '{col}' contains a mix of different data types. This prevents proper "
                        f"numerical operations and comparisons. Mixed types are often caused by data entry "
                        f"errors, such as text appearing in a numeric column."
                    ),
                    'action': (
                        f"Use the 'Fix Data Types' cleaning operation to convert '{col}' to a consistent type. "
                        f"Values that cannot be converted will become null and can then be filled using "
                        f"the missing value handling feature."
                    ),
                    'auto_fixable': True,
                    'fix_operation': {
                        'type': 'fix_data_types',
                        'params': {'columns': [col]},
                    },
                })
            elif issue['type'] == 'type_mismatch':
                self.recommendations.append({
                    'id': f'type_mismatch_{col}',
                    'category': 'Data Types',
                    'priority': 'medium',
                    'column': col,
                    'title': f"Type mismatch in '{col}'",
                    'explanation': (
                        f"Column '{col}' is stored as text but appears to contain numeric or date data. "
                        f"This prevents mathematical operations and proper sorting."
                    ),
                    'action': (
                        f"Convert '{col}' to the appropriate data type using the 'Fix Data Types' feature. "
                        f"This will enable proper numerical analysis and sorting."
                    ),
                    'auto_fixable': True,
                    'fix_operation': {
                        'type': 'fix_data_types',
                        'params': {'columns': [col]},
                    },
                })

    def _recommend_outliers(self):
        """Generate recommendations for outlier issues."""
        outlier_issues = [i for i in self.issues if i['type'] == 'outliers']
        if not outlier_issues:
            return

        for issue in outlier_issues:
            col = issue['column']
            count = issue['affected_rows']
            pct = issue['affected_pct']
            profile = self.column_profiles.get(col, {})

            col_min = profile.get('min', '?')
            col_max = profile.get('max', '?')
            col_mean = profile.get('mean', '?')
            col_median = profile.get('median', '?')

            if pct > 10:
                explanation = (
                    f"Column '{col}' has {count} outliers ({pct}%) — a high proportion suggesting "
                    f"possible data quality issues rather than natural variation. "
                    f"Range: [{col_min}, {col_max}], Mean: {col_mean}, Median: {col_median}. "
                    f"The gap between mean and median ({round(abs(col_mean - col_median), 2) if isinstance(col_mean, (int, float)) and isinstance(col_median, (int, float)) else 'N/A'}) "
                    f"indicates skewness caused by extreme values."
                )
                priority = 'high'
            elif pct > 3:
                explanation = (
                    f"Column '{col}' has {count} statistical outliers ({pct}%). "
                    f"These values fall outside the expected range based on the IQR method. "
                    f"Data range: [{col_min}, {col_max}]."
                )
                priority = 'medium'
            else:
                explanation = (
                    f"Column '{col}' has {count} mild outliers ({pct}%). "
                    f"A small number of values outside the typical range."
                )
                priority = 'low'

            self.recommendations.append({
                'id': f'outliers_{col}',
                'category': 'Outliers',
                'priority': priority,
                'column': col,
                'title': f"{count} outliers in '{col}' ({pct}%)",
                'explanation': explanation,
                'action': (
                    f"Cap outliers in '{col}' at the IQR boundaries (Winsorization) to limit extreme values "
                    f"while preserving the data points. Alternatively, remove outlier rows if they represent "
                    f"errors rather than genuine extreme values. Use 'Handle Outliers' with the 'cap' method "
                    f"for a conservative approach."
                ),
                'auto_fixable': True,
                'fix_operation': {
                    'type': 'handle_outliers',
                    'params': {'columns': [col], 'method': 'cap'},
                },
            })

    def _recommend_invalid_values(self):
        """Generate recommendations for invalid value issues."""
        invalid_types = ['invalid_email', 'invalid_phone', 'negative_values',
                         'unreasonable_age', 'invalid_date', 'whitespace_only']
        invalid_issues = [i for i in self.issues if i['type'] in invalid_types]

        for issue in invalid_issues:
            col = issue['column']
            count = issue['affected_rows']
            issue_type = issue['type']

            explanations = {
                'invalid_email': (
                    f"Column '{col}' contains {count} values that don't match standard email format. "
                    f"These could be typos, incomplete entries, or non-email data incorrectly placed in this column."
                ),
                'invalid_phone': (
                    f"Column '{col}' has {count} values that don't match phone number patterns. "
                    f"Check for formatting inconsistencies or non-phone data."
                ),
                'negative_values': (
                    f"Column '{col}' contains {count} negative values in a field where negatives are "
                    f"semantically invalid (e.g., age, price, quantity). These likely represent data entry errors."
                ),
                'unreasonable_age': (
                    f"Column '{col}' has {count} age values outside the reasonable range (0-150). "
                    f"These are likely data entry errors or placeholder values."
                ),
                'invalid_date': (
                    f"Column '{col}' contains {count} dates that are invalid or in the future. "
                    f"These should be verified and corrected."
                ),
                'whitespace_only': (
                    f"Column '{col}' has {count} values that contain only whitespace characters. "
                    f"These are effectively missing values disguised as non-empty cells."
                ),
            }

            actions = {
                'invalid_email': f"Review and correct invalid email addresses in '{col}'. Consider using validation rules during data entry to prevent future issues.",
                'invalid_phone': f"Standardize phone number format in '{col}'. Apply consistent formatting (e.g., international format with country code).",
                'negative_values': f"Review negative values in '{col}' and correct or replace them. These can be handled as outliers using the cleaning feature.",
                'unreasonable_age': f"Review unreasonable age values in '{col}'. Replace with null and then use imputation, or investigate the source data.",
                'invalid_date': f"Review and correct invalid dates in '{col}'. Ensure consistent date format across the column.",
                'whitespace_only': f"Convert whitespace-only values in '{col}' to proper null values using the 'Standardize Values' cleaning operation.",
            }

            self.recommendations.append({
                'id': f'{issue_type}_{col}',
                'category': 'Invalid Values',
                'priority': issue['severity'],
                'column': col,
                'title': f"{count} {issue_type.replace('_', ' ')} in '{col}'",
                'explanation': explanations.get(issue_type, issue['description']),
                'action': actions.get(issue_type, "Review and correct the invalid values."),
                'auto_fixable': issue_type == 'whitespace_only',
                'fix_operation': {
                    'type': 'standardize_values',
                    'params': {'columns': [col]},
                } if issue_type == 'whitespace_only' else None,
            })

    def _recommend_consistency(self):
        """Generate recommendations for consistency issues."""
        consistency_types = ['case_inconsistency', 'whitespace_issues', 'extra_whitespace']
        consistency_issues = [i for i in self.issues if i['type'] in consistency_types]

        for issue in consistency_issues:
            col = issue['column']
            count = issue['affected_rows']
            issue_type = issue['type']

            if issue_type == 'case_inconsistency':
                consistency_data = self.results.get('consistency', {}).get('columns', {}).get(col, {})
                examples = consistency_data.get('issues', {}).get('case_inconsistency', {}).get('examples', [])
                example_str = ""
                if examples:
                    example_str = " Examples: " + ", ".join(
                        f"'{'/'.join(e)}'" for e in examples[:2]
                    )

                self.recommendations.append({
                    'id': f'case_{col}',
                    'category': 'Consistency',
                    'priority': issue['severity'],
                    'column': col,
                    'title': f"Case inconsistencies in '{col}'",
                    'explanation': (
                        f"Column '{col}' has {count} values that differ only by letter casing. "
                        f"This means the same entity is represented differently, which will cause "
                        f"incorrect grouping, counting, and joins.{example_str}"
                    ),
                    'action': (
                        f"Use 'Standardize Values' to normalize case in '{col}'. "
                        f"The system will apply title case for name columns and consistent formatting for others."
                    ),
                    'auto_fixable': True,
                    'fix_operation': {
                        'type': 'standardize_values',
                        'params': {'columns': [col], 'normalize_case': True},
                    },
                })

            elif issue_type in ('whitespace_issues', 'extra_whitespace'):
                self.recommendations.append({
                    'id': f'whitespace_{col}',
                    'category': 'Consistency',
                    'priority': issue['severity'],
                    'column': col,
                    'title': f"Whitespace issues in '{col}'",
                    'explanation': (
                        f"Column '{col}' has {count} values with leading, trailing, or extra internal whitespace. "
                        f"This invisible inconsistency causes string matching and lookup failures."
                    ),
                    'action': (
                        f"Apply 'Standardize Values' to trim whitespace and normalize spacing in '{col}'."
                    ),
                    'auto_fixable': True,
                    'fix_operation': {
                        'type': 'standardize_values',
                        'params': {'columns': [col], 'trim_whitespace': True, 'normalize_whitespace': True},
                    },
                })

    def _recommend_overall(self):
        """Generate overall dataset-level recommendations."""
        score = self.results.get('overall_score', 100)
        total_issues = len(self.issues)

        if score < 50:
            self.recommendations.insert(0, {
                'id': 'overall_quality',
                'category': 'Overall',
                'priority': 'critical',
                'column': 'ALL',
                'title': f"Dataset quality score is critically low ({score}/100)",
                'explanation': (
                    f"The overall data quality score is {score}/100 with {total_issues} issues detected. "
                    f"This dataset requires significant cleaning before it can be reliably used for analysis. "
                    f"Category breakdown — Completeness: {self.category_scores.get('completeness', 0)}, "
                    f"Uniqueness: {self.category_scores.get('uniqueness', 0)}, "
                    f"Validity: {self.category_scores.get('validity', 0)}, "
                    f"Consistency: {self.category_scores.get('consistency', 0)}, "
                    f"Accuracy: {self.category_scores.get('accuracy', 0)}."
                ),
                'action': (
                    "Use the 'Apply All Fixes' option to automatically clean the most impactful issues. "
                    "Start with removing duplicates, then fill missing values, and finally handle outliers. "
                    "Review the preview before downloading the cleaned dataset."
                ),
                'auto_fixable': True,
                'fix_operation': None,
            })
        elif score < 75:
            self.recommendations.insert(0, {
                'id': 'overall_quality',
                'category': 'Overall',
                'priority': 'high',
                'column': 'ALL',
                'title': f"Dataset quality needs improvement ({score}/100)",
                'explanation': (
                    f"The quality score of {score}/100 indicates several areas need attention. "
                    f"{total_issues} issues were found across the dataset. "
                    f"The lowest scoring category is "
                    f"{min(self.category_scores, key=self.category_scores.get) if self.category_scores else 'N/A'} "
                    f"({min(self.category_scores.values()) if self.category_scores else 0}/100)."
                ),
                'action': (
                    "Address the high-priority issues first using the automated cleaning tools. "
                    "Focus on the lowest-scoring quality category for maximum improvement."
                ),
                'auto_fixable': True,
                'fix_operation': None,
            })
