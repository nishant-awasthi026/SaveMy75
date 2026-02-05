from doctr.io import DocumentFile
from doctr.models import ocr_predictor
import re
import numpy as np

class AttendanceAnalyzer:
    def __init__(self):
        # Initialize DocTR predictor (Pretrained)
        # We use a basic pretrained model (det: db_resnet50, reco: crnn_vgg16_bn)
        # Initialize DocTR predictor (Pretrained)
        # Using MobileNet backends to fit within 512MB RAM on free tier cloud hosting
        self.predictor = ocr_predictor(det_arch='db_mobilenet_v3_large', reco_arch='crnn_mobilenet_v3_large', pretrained=True)

    def analyze_image(self, image_path):
        """
        Analyzes an image using DocTR and extracts structured attendance data.
        """
        try:
            # Load image
            doc = DocumentFile.from_images(image_path)
            # Predict
            result = self.predictor(doc)
            
            # Extract words with geometry
            words = self._extract_words(result)
            
            # Group into rows
            rows = self._group_by_rows(words)
            
            # Parse rows into course data
            structured_data = self._parse_rows(rows)
            
            return structured_data
        except Exception as e:
            print(f"Error in OCR analysis: {e}")
            return []

    def _extract_words(self, result):
        """
        Flatten hierarchical docTR result into a list of words with geometry.
        Returns: [{'text': str, 'y': float, 'x': float, 'h': float, 'w': float}, ...]
        Note: docTR geometry is relative (0.0 to 1.0).
        """
        words = []
        for page in result.pages:
            for block in page.blocks:
                for line in block.lines:
                    for word in line.words:
                        # word.geometry = ((x_min, y_min), (x_max, y_max))
                        (x_min, y_min), (x_max, y_max) = word.geometry
                        
                        # Center Y for row grouping
                        center_y = (y_min + y_max) / 2
                        center_x = (x_min + x_max) / 2
                        
                        words.append({
                            'text': word.value,
                            'y': center_y,
                            'x': center_x,
                            'y_min': y_min,
                            'y_max': y_max,
                            'x_min': x_min
                        })
        return words

    def _group_by_rows(self, words, y_threshold=0.02):
        """
        Groups words into rows based on Y-coordinate.
        y_threshold is relative (default 0.02 = 2% of page height).
        """
        if not words:
            return []
            
        # Sort words by Y-center
        sorted_words = sorted(words, key=lambda w: w['y'])
        
        rows = []
        current_row = [sorted_words[0]]
        current_y_avg = sorted_words[0]['y']
        
        for word in sorted_words[1:]:
            # If word overlaps significantly with current row's average Y
            if abs(word['y'] - current_y_avg) <= y_threshold:
                current_row.append(word)
                # Update moving average of Y for robust grouping
                current_y_avg = np.mean([w['y'] for w in current_row])
            else:
                # New row
                rows.append(current_row)
                current_row = [word]
                current_y_avg = word['y']
        
        rows.append(current_row)
        
        # Sort each row by X-coordinate
        for row in rows:
            row.sort(key=lambda w: w['x'])
        
        return rows

    def _parse_rows(self, rows):
        """
        Logic to extract Course, Attended, Total from textual rows.
        Supports both inline "Course Name Total Attended" and split "Code Stats" ... "Code - Name" layouts.
        """
        attendance_entries = [] # List of {code, partial_name, numbers, ...}
        course_mappings = {}    # Dict of code -> full_name
        
        for row in rows:
            # Reconstruct full text line and separate numbers
            text_parts = []
            numbers = []
            percentages = []
            
            # Check if this row is likely a "Total" summary row
            row_text_full = " ".join([item['text'] for item in row]).lower()
            if 'total' in row_text_full or 'grand' in row_text_full:
                continue

            # Sort items by X-coordinate to establish left-to-right reading order
            row.sort(key=lambda w: w['x'])
            row_text_items = [item['text'] for item in row]
            
            # Heuristic: The right-most number is often the Percentage/Status column.
            # Attempt to identify the last numeric token as a potential percentage.
            last_number_idx = -1
            for idx in range(len(row)-1, -1, -1):
                txt = row[idx]['text'].strip()
                if re.match(r'^\d+(\.\d+)?%?$', txt):
                    last_number_idx = idx
                    break
            
            potential_percentage_val = None
            if last_number_idx != -1:
                txt = row[last_number_idx]['text'].strip().replace('%', '')
                try:
                    val = float(txt)
                    if 0 <= val <= 100:
                        potential_percentage_val = val
                except: pass

            for i, text in enumerate(row_text_items):
                clean_text = text.strip()
                
                # Check for explicit percentage strings (e.g., "75.0%")
                if '%' in clean_text:
                    try:
                        val = float(clean_text.replace('%', ''))
                        percentages.append(val)
                    except: pass
                
                # Check for standalone '%' symbol and use the previous token if numeric
                if clean_text == '%' and i > 0:
                   prev_text = row_text_items[i-1].strip()
                   if re.match(r'^\d+(\.\d+)?$', prev_text):
                        try:
                           val = float(prev_text)
                           if val not in percentages:
                               percentages.append(val)
                        except: pass

                # Categorize numeric values
                if re.match(r'^\d+$', clean_text):
                     numbers.append(int(clean_text))
                elif re.match(r'^\d+\.\d+$', clean_text):
                    try:
                        val = float(clean_text)
                        # Integers represented as floats (e.g. 20.0) are treated as numbers.
                        if val.is_integer():
                             numbers.append(int(val))
                        else:
                             # Decimal values (e.g., 73.91) are treated as percentages.
                             if 0 <= val <= 100 and val not in percentages:
                                 percentages.append(val)
                    except: pass
                else:
                    # Collect remaining text parts (potential course names)
                    if not re.match(r'^[\d\W]+$', clean_text): 
                         if clean_text.lower() not in ['attended', 'max', 'hours', 'percentage', 'status', 'classes', 'of', 'total', 'legend:', 'updated:']:
                             text_parts.append(clean_text)
            
            # Include geometrically detected percentage if not already found
            if potential_percentage_val is not None and potential_percentage_val not in percentages:
                percentages.append(potential_percentage_val)

            # Identify Potential Course Code
            course_code = None
            if len(row_text_items) > 0:
                first_word = row_text_items[0].strip()
                if len(first_word) >= 4 and any(c.isdigit() for c in first_word) and any(c.isalpha() for c in first_word):
                    course_code = first_word
            
            # CASE 1: Data Row
            match_found = False
            best_pair = None
            unique_nums = sorted(list(set(numbers)))
            
            # Strategy 1: Percentage Validation
            # Checks if any pair of numbers (Attended / Total) matches the detected percentage (p).
            # Handles correct cases including 100% (where Attended == Total).
            if not match_found and percentages and len(unique_nums) >= 1:
                for p in percentages:
                    # Special Case: 100%
                    if abs(100 - p) < 1.0:
                        candidates = [n for n in unique_nums if n > 0]
                        if candidates:
                            # If 100%, the largest candidate is likely the Total/Attended count.
                            best_val = max(candidates)
                            best_pair = (best_val, best_val)
                            match_found = True
                            break
                    
                    # Standard Case: Check all pairs
                    if len(unique_nums) >= 2:
                        for i in range(len(unique_nums)):
                            for j in range(len(unique_nums)):
                                if i == j: continue
                                a, b = unique_nums[i], unique_nums[j]
                                if b == 0 or a > b: continue
                                
                                if abs((a/b)*100 - p) < 1.0:
                                    best_pair = (a, b)
                                    match_found = True
                                    break
                            if match_found: break
                    if match_found: break

            # Strategy 2: Difference Check
            # Verifies the mathematical relationship: Total - Attended = Absent.
            # Used when valid numbers are found but the percentage calculation is ambiguous or missing.
            if not match_found and len(unique_nums) >= 3:
                for i in range(len(unique_nums)):
                    for j in range(len(unique_nums)):
                        if i == j: continue
                        total_cand = unique_nums[i]
                        attended_cand = unique_nums[j]
                        if total_cand <= attended_cand: continue
                        
                        absent_cand = total_cand - attended_cand
                        if absent_cand in unique_nums:
                            # Note: This method assumes the standard layout where Attended hours 
                            # are distinguishable or follow the Total - Attended logic.
                            best_pair = (attended_cand, total_cand)
                            match_found = True
                            break
                    if match_found: break

            # Strategy 2: Difference Check (Total - Attended = Absent)
            # This is very robust for "Total Attended Absent" format
            if not match_found and len(unique_nums) >= 3:
                # We need A, B, C such that A - B = C
                for i in range(len(unique_nums)):
                    for j in range(len(unique_nums)):
                        if i == j: continue
                        total_cand = unique_nums[i]
                        attended_cand = unique_nums[j]
                        
                        if total_cand <= attended_cand: continue
                        
                        absent_cand = total_cand - attended_cand
                        if absent_cand in unique_nums:
                            # Found it!
                            best_pair = (attended_cand, total_cand)
                            match_found = True
                            break
                    if match_found: break
            
            # Strategy 3: Two-Number Fallback
            # If only two numbers exist, assume the smaller is Attended and larger is Total.
            if not match_found and len(unique_nums) == 2:
                 best_pair = (unique_nums[0], unique_nums[1])
                 match_found = True

            # Strategy 4: Largest Integers Fallback
            # If all else fails, attempt to guess based on the largest available integers,
            # excluding outliers like year numbers (>= 500).
            if not match_found and len(unique_nums) >= 2:
                candidates = []
                for n in unique_nums:
                    if n >= 500: continue 
                    candidates.append(n)
                
                candidates.sort(reverse=True)
                
                # Use geometric percentage hint to refine candidate selection
                if potential_percentage_val is not None:
                     # Attempt to find a pair matching the geometric percentage
                     for i in range(len(candidates)):
                        for j in range(len(candidates)):
                             if i == j: continue
                             a = candidates[j] # Attended (Smaller)
                             b = candidates[i] # Total (Larger)
                             if b == 0 or a > b: continue
                             
                             if abs((a/b)*100 - potential_percentage_val) < 1.0:
                                 best_pair = (a, b)
                                 match_found = True
                                 break
                        if match_found: break

                # Final fallback: Exclude the number that matches the percentage value,
                # then pick the next largest pair.
                if not match_found and len(candidates) >= 2:
                     first_candidate = candidates[0]
                     if potential_percentage_val is not None and abs(first_candidate - potential_percentage_val) < 0.1:
                         # The largest number is likely the percentage value itself.
                         if len(candidates) >= 3:
                             # Use the next two largest numbers (Attended/Total)
                             best_pair = (candidates[2], candidates[1])
                             match_found = True
                         elif len(candidates) == 2:
                             # Insufficient data to determine Total/Attended
                             pass
                     else:
                        # Default to the two largest numbers
                        best_pair = (candidates[1], candidates[0])
                        match_found = True

            if match_found:
                # This is an attendance row
                # If we have text parts, they might be the name OR just the code and junk
                name = " ".join(text_parts)
                # If the name starts with the code, strip it?
                # Actually, we rely on mapping if the name is short or just code
                attendance_entries.append({
                    "code": course_code,
                    "name": name,
                    "attended": best_pair[0],
                    "total": best_pair[1]
                })
            
            # CASE 2: Mapping Row (No attendance numbers, but has Code + Text)
            elif course_code and len(text_parts) > 1 and not numbers:
                # Legend row: "21CSC303J - SOFTWARE ENGINEERING"
                # Join text parts, remove code if present
                full_text = " ".join(text_parts)
                # Remove code from text if it's there
                clean_name = full_text.replace(course_code, "").strip(" -:")
                if len(clean_name) > 3:
                     course_mappings[course_code] = clean_name

        # Merge Entries and Mappings
        final_data = []
        for entry in attendance_entries:
            display_name = entry['name']
            code = entry['code']
            
            # If name is empty or looks like just the code, try to find mapping
            is_name_bad = len(display_name) < 5 or display_name == code
            
            if code and code in course_mappings:
                # We have a better name in mapping
                # But sometimes the mapping key might be slightly fuzzy? 
                # Assuming exact match for now as OCR is usually consistent on codes
                display_name = f"{code} {course_mappings[code]}"
            elif is_name_bad and code:
                display_name = code # Better than nothing
                
            final_data.append({
                "course": display_name,
                "attended": entry['attended'],
                "total": entry['total']
            })
                 
        return final_data
