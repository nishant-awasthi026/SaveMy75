from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import json

def debug_mobile():
    image_path = "mock data/mobile version.jpeg"
    print(f"Analyzing {image_path}...")
    
    # Init predictor directly
    predictor = ocr_predictor(det_arch='db_resnet50', reco_arch='crnn_vgg16_bn', pretrained=True)
    doc = DocumentFile.from_images(image_path)
    result = predictor(doc)
    
    words = []
    for page in result.pages:
        for block in page.blocks:
            for line in block.lines:
                for word in line.words:
                    (x_min, y_min), (x_max, y_max) = word.geometry
                    center_y = (y_min + y_max) / 2
                    center_x = (x_min + x_max) / 2
                    words.append({
                        'text': word.value,
                        'y': round(center_y, 3),
                        'x': round(center_x, 3),
                        'w': round(x_max - x_min, 3),
                        'h': round(y_max - y_min, 3)
                    })
    
    # Print a sample of words to see structure
    print("Raw Words (Sample):")
    print(json.dumps(words[:20], indent=2))
    
    # Try to visualize clustering by Y
    print("\n--- Rows by Y (Threshold 0.02) ---")
    
    # Simple cluster
    sorted_words = sorted(words, key=lambda w: w['y'])
    if not sorted_words: return

    rows = []
    current_row = [sorted_words[0]]
    current_y = sorted_words[0]['y']
    
    for w in sorted_words[1:]:
        if abs(w['y'] - current_y) < 0.02:
            current_row.append(w)
        else:
            # Sort row by X
            current_row.sort(key=lambda x: x['x'])
            rows.append(current_row)
            current_row = [w]
            current_y = w['y']
    rows.append(current_row)
    
    for i, row in enumerate(rows):
        # Sort by x
        row.sort(key=lambda w: w['x'])
        text_with_geom = " | ".join([f"{w['text']} (x={w['x']:.2f})" for w in row])
        print(f"Row {i}: {text_with_geom}")
        
    print("\n--- Parsed Data ---")
    # Use the analyzer instance to parse
    analyzer = AttendanceAnalyzer()
    parsed = analyzer._parse_rows(rows)
    print(json.dumps(parsed, indent=2))
