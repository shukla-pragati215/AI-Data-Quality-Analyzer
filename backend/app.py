"""
Flask Application — AI Data Quality Analyzer API
"""

import os
import uuid
import json
import traceback
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
import pandas as pd
import numpy as np

from analyzer import DataQualityAnalyzer
from cleaner import DataCleaner
from recommender import AIRecommender
from report_generator import ReportGenerator

app = Flask(__name__, static_folder=None)
CORS(app)

# Configuration
# Vercel functions can only write to /tmp; local development keeps using uploads/.
UPLOAD_FOLDER = os.environ.get(
    'UPLOAD_FOLDER',
    '/tmp/ai-data-quality-analyzer' if os.environ.get('VERCEL') else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'uploads'
    ),
)
ALLOWED_EXTENSIONS = {'csv', 'xlsx', 'xls'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# In-memory session store (maps session_id to data)
sessions = {}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def read_dataset(filepath):
    """Read a CSV or Excel file into a DataFrame."""
    ext = filepath.rsplit('.', 1)[1].lower()
    if ext == 'csv':
        # Try common encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252', 'iso-8859-1']:
            try:
                return pd.read_csv(filepath, encoding=encoding)
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        raise ValueError("Could not read CSV file with any supported encoding")
    elif ext in ('xlsx', 'xls'):
        return pd.read_excel(filepath)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


# ── Serve Frontend ──────────────────────────────────────────────────────────

FRONTEND_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'frontend')


@app.route('/')
def serve_index():
    return send_from_directory(FRONTEND_FOLDER, 'index.html')


@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(FRONTEND_FOLDER, filename)


# ── API Endpoints ───────────────────────────────────────────────────────────

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload and validate a dataset file."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({
                'error': f'Invalid file type. Supported formats: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        # Check file size
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > MAX_FILE_SIZE:
            return jsonify({
                'error': f'File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB'
            }), 400

        # Save file
        session_id = str(uuid.uuid4())
        ext = file.filename.rsplit('.', 1)[1].lower()
        saved_filename = f"{session_id}.{ext}"
        filepath = os.path.join(UPLOAD_FOLDER, saved_filename)
        file.save(filepath)

        # Read and validate
        try:
            df = read_dataset(filepath)
        except Exception as e:
            os.remove(filepath)
            return jsonify({
                'error': f'Could not read file: {str(e)}. Please check the file format and contents.'
            }), 400

        if df.empty:
            os.remove(filepath)
            return jsonify({'error': 'The file is empty or contains no readable data'}), 400

        if len(df.columns) < 1:
            os.remove(filepath)
            return jsonify({'error': 'No columns found in the dataset'}), 400

        # Store session
        sessions[session_id] = {
            'filepath': filepath,
            'filename': file.filename,
            'df': df,
            'cleaned_df': None,
            'analysis': None,
            'recommendations': None,
            'cleaning_result': None,
        }

        return jsonify({
            'session_id': session_id,
            'filename': file.filename,
            'rows': len(df),
            'columns': len(df.columns),
            'column_names': df.columns.tolist(),
            'preview': {
                'columns': df.columns.tolist(),
                'rows': df.head(10).fillna('').astype(str).values.tolist(),
            },
            'file_size_mb': round(size / (1024 * 1024), 2),
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


@app.route('/api/analysis/<session_id>', methods=['GET'])
def run_analysis(session_id):
    """Run full data quality analysis."""
    try:
        session = sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found. Please re-upload your file.'}), 404

        df = session['df']
        filename = session['filename']

        # Run analysis
        analyzer = DataQualityAnalyzer(df, filename)
        analysis = analyzer.run_full_analysis()

        # Generate recommendations
        recommender = AIRecommender(analysis)
        recommendations = recommender.generate_recommendations()

        # Store results
        session['analysis'] = analysis
        session['recommendations'] = recommendations

        # Make response JSON-safe
        response = {
            'analysis': _make_json_safe(analysis),
            'recommendations': _make_json_safe(recommendations),
        }

        return jsonify(response)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Analysis failed: {str(e)}'}), 500


@app.route('/api/clean/<session_id>', methods=['POST'])
def clean_dataset(session_id):
    """Apply cleaning operations to the dataset."""
    try:
        session = sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found. Please re-upload your file.'}), 404

        operations = request.json.get('operations', [])
        if not operations:
            return jsonify({'error': 'No cleaning operations specified'}), 400

        df = session['df']

        # Apply cleaning
        cleaner = DataCleaner(df)
        result = cleaner.apply_operations(operations)

        cleaned_df = cleaner.get_cleaned_dataframe()
        preview = cleaner.get_preview(20)

        # Re-analyze cleaned dataset for before/after scores
        analyzer_after = DataQualityAnalyzer(cleaned_df, session['filename'])
        analysis_after = analyzer_after.run_full_analysis()

        # Store
        session['cleaned_df'] = cleaned_df
        session['cleaning_result'] = result

        response = {
            'cleaning_result': _make_json_safe(result),
            'preview': _make_json_safe(preview),
            'before_score': session['analysis']['overall_score'] if session['analysis'] else None,
            'after_score': analysis_after['overall_score'],
            'before_category_scores': _make_json_safe(session['analysis']['category_scores']) if session['analysis'] else None,
            'after_category_scores': _make_json_safe(analysis_after['category_scores']),
            'after_issues_count': len(analysis_after['issues']),
            'before_issues_count': len(session['analysis']['issues']) if session['analysis'] else 0,
        }

        return jsonify(response)

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Cleaning failed: {str(e)}'}), 500


@app.route('/api/preview/<session_id>', methods=['GET'])
def preview_data(session_id):
    """Preview original and optionally cleaned data."""
    try:
        session = sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        n = request.args.get('rows', 20, type=int)
        n = min(n, 100)

        df = session['df']
        result = {
            'original': {
                'columns': df.columns.tolist(),
                'rows': df.head(n).fillna('').astype(str).values.tolist(),
                'total_rows': len(df),
            }
        }

        if session.get('cleaned_df') is not None:
            cdf = session['cleaned_df']
            result['cleaned'] = {
                'columns': cdf.columns.tolist(),
                'rows': cdf.head(n).fillna('').astype(str).values.tolist(),
                'total_rows': len(cdf),
            }

        return jsonify(result)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<session_id>/<file_type>', methods=['GET'])
def download_file(session_id, file_type):
    """Download cleaned dataset as CSV or Excel."""
    try:
        session = sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        cleaned_df = session.get('cleaned_df')
        if cleaned_df is None:
            return jsonify({'error': 'No cleaned dataset available. Please run cleaning first.'}), 400

        original_name = session['filename'].rsplit('.', 1)[0]

        if file_type == 'csv':
            filepath = os.path.join(UPLOAD_FOLDER, f"{session_id}_cleaned.csv")
            cleaned_df.to_csv(filepath, index=False)
            return send_file(
                filepath,
                as_attachment=True,
                download_name=f"{original_name}_cleaned.csv",
                mimetype='text/csv'
            )
        elif file_type == 'xlsx':
            filepath = os.path.join(UPLOAD_FOLDER, f"{session_id}_cleaned.xlsx")
            cleaned_df.to_excel(filepath, index=False)
            return send_file(
                filepath,
                as_attachment=True,
                download_name=f"{original_name}_cleaned.xlsx",
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        else:
            return jsonify({'error': 'Invalid file type. Use csv or xlsx.'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/report/<session_id>', methods=['GET'])
def download_report(session_id):
    """Generate and download PDF analysis report."""
    try:
        session = sessions.get(session_id)
        if not session:
            return jsonify({'error': 'Session not found'}), 404

        analysis = session.get('analysis')
        recommendations = session.get('recommendations', [])

        if not analysis:
            return jsonify({'error': 'No analysis results available. Please run analysis first.'}), 400

        generator = ReportGenerator(analysis, recommendations)
        pdf_bytes = generator.generate_pdf()

        original_name = session['filename'].rsplit('.', 1)[0]
        report_path = os.path.join(UPLOAD_FOLDER, f"{session_id}_report.pdf")
        with open(report_path, 'wb') as f:
            f.write(pdf_bytes)

        return send_file(
            report_path,
            as_attachment=True,
            download_name=f"{original_name}_quality_report.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        traceback.print_exc()
        return jsonify({'error': f'Report generation failed: {str(e)}'}), 500


def _make_json_safe(obj):
    """Convert numpy/pandas types to JSON-serializable Python types."""
    if isinstance(obj, dict):
        return {k: _make_json_safe(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_make_json_safe(v) for v in obj]
    elif isinstance(obj, (np.integer,)):
        return int(obj)
    elif isinstance(obj, (np.floating,)):
        if np.isnan(obj) or np.isinf(obj):
            return None
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.bool_,)):
        return bool(obj)
    elif isinstance(obj, pd.Timestamp):
        return obj.isoformat()
    elif isinstance(obj, float):
        if obj != obj or obj == float('inf') or obj == float('-inf'):
            return None
        return obj
    return obj


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print("  AI Data Quality Analyzer")
    print("  Server running at: http://localhost:5000")
    print("=" * 60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
