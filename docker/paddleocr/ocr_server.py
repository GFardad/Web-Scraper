"""
PaddleOCR HTTP Server - GPU-Accelerated OCR API

Provides a simple HTTP API wrapper around PaddleOCR for text extraction.
Designed to run in Docker container with GPU pass through.

Endpoints:
    POST /ocr - Extract text from image
    GET /health - Health check

Usage:
    curl -X POST -F "image=@screenshot.png" http://localhost:8000/ocr
"""

import sys
import os
import json
import logging
from io import BytesIO
from typing import List, Dict, Any

# GPU configuration
os.environ['CUDA_VISIBLE_DEVICES'] = '0'

try:
    from paddleocr import PaddleOCR
except ImportError:
    print("ERROR: PaddleOCR not installed. Install with: pip install paddleocr")
    sys.exit(1)

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from PIL import Image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Initialize PaddleOCR (GPU-enabled)
logger.info("Initializing PaddleOCR with GPU support...")
try:
    ocr = PaddleOCR(
        use_angle_cls=True,  # Enable text angle classification
        lang='en',  # English language
        use_gpu=True,  # CRITICAL: Enable GPU
        gpu_mem=700,  # Reserve 700MB VRAM (within 3GB budget)
        show_log=False  # Reduce verbosity
    )
    logger.info("✅ PaddleOCR initialized successfully with GPU")
except Exception as e:
    logger.error(f"❌ Failed to initialize PaddleOCR: {e}")
    sys.exit(1)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}

def allowed_file(filename: str) -> bool:
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'service': 'paddleocr',
        'gpu_enabled': True
    }), 200


@app.route('/ocr', methods=['POST'])
def extract_text():
    """
    Extract text from uploaded image using PaddleOCR.
    
    Request:
        POST /ocr
        Content-Type: multipart/form-data
        Body: image file
    
    Response:
        {
            "success": true,
            "text_blocks": [
                {
                    "text": "extracted text",
                    "confidence": 0.95,
                    "bbox": [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                }
            ],
            "full_text": "concatenated text"
        }
    """
    try:
        # Check if image is in request
        if 'image' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No image file provided'
            }), 400
        
        file = request.files['image']
        
        # Check if file is valid
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': 'Empty filename'
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'Invalid file type. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # Read image
        image_bytes = file.read()
        image = Image.open(BytesIO(image_bytes))
        
        # Convert to RGB if needed
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Run OCR
        logger.info(f"Running OCR on image: {file.filename} ({image.size})")
        result = ocr.ocr(image_bytes, cls=True)
        
        # Parse results
        text_blocks = []
        full_text_parts = []
        
        if result and result[0]:
            for line in result[0]:
                bbox = line[0]  # Bounding box coordinates
                text_data = line[1]  # (text, confidence)
                
                text_blocks.append({
                    'text': text_data[0],
                    'confidence': float(text_data[1]),
                    'bbox': bbox
                })
                
                full_text_parts.append(text_data[0])
        
        full_text = ' '.join(full_text_parts)
        
        logger.info(f"OCR extracted {len(text_blocks)} text blocks")
        
        return jsonify({
            'success': True,
            'text_blocks': text_blocks,
            'full_text': full_text,
            'block_count': len(text_blocks)
        }), 200
        
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/extract_price', methods=['POST'])
def extract_price():
    """
    Specialized endpoint for price extraction.
    Filters OCR results to find price-like patterns.
    
    Response:
        {
            "success": true,
            "prices": [
                {
                    "value": "99.99",
                    "currency": "$",
                    "confidence": 0.95,
                    "full_text": "$99.99"
                }
            ]
        }
    """
    import re
    
    try:
        # Reuse /ocr logic
        ocr_response = extract_text()
        ocr_data = json.loads(ocr_response[0].get_data(as_text=True))
        
        if not ocr_data.get('success'):
            return ocr_response
        
        # Price extraction patterns
        price_patterns = [
            r'[\$€£¥₹]\s*([0-9,]+\.?[0-9]*)',  # Currency symbol + number
            r'([0-9,]+\.?[0-9]*)\s*[\$€£¥₹]',  # Number + currency symbol
            r'([0-9,]+\.?[0-9]*)\s*(USD|EUR|GBP|JPY|INR)',  # Number + currency code
        ]
        
        prices = []
        
        for block in ocr_data['text_blocks']:
            text = block['text']
            
            for pattern in price_patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                if matches:
                    for match in matches:
                        price_value = match[0] if isinstance(match, tuple) else match
                        prices.append({
                            'value': price_value.replace(',', ''),
                            'currency': text[0] if text[0] in '$€£¥₹' else '',
                            'confidence': block['confidence'],
                            'full_text': text
                        })
        
        return jsonify({
            'success': True,
            'prices': prices,
            'price_count': len(prices)
        }), 200
        
    except Exception as e:
        logger.error(f"Price extraction failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    logger.info("🚀 Starting PaddleOCR Server on port 8000")
    logger.info(f"   GPU Enabled: True")
    logger.info(f"   VRAM Allocated: 700MB")
    logger.info(f"   Language: English")
    
    # Run server
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=False,
        threaded=True
    )
