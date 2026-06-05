#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 00:41:20 2026

@author: brennen
"""

import sys
from pathlib import Path
import argparse
import time
import xml.etree.ElementTree as ET

try:
    import pandas as pd
except ImportError:
    print("Error: The 'pandas' library is required. Install it using 'pip install pandas openpyxl'.")
    sys.exit(1)

def generate_bob(excel_path, output_path):
    try:
        df = pd.read_excel(excel_path, engine='openpyxl')
    except ValueError as ve:
        print(f"  -> Format Error: Ensure openpyxl is installed and the file is a valid .xlsx file. ({ve})")
        return
    except Exception as e:
        print(f"  -> Error loading {excel_path.name}: {e}")
        return

    df = df.dropna(subset=['Record Type', 'Record Name'])

    root = ET.Element("display", version="2.0.0")
    ET.SubElement(root, "name").text = f"Batch Testing Screen - {excel_path.stem}"
    
    ET.SubElement(root, "width").text = "1200"
    ET.SubElement(root, "height").text = "1200"

    START_X = 50
    X_SPACING = 180
    START_Y = 80
    Y_SPACING = 35

    x_positions = {}
    y_counters = {}
    widgets_added = 0

    for _, row in df.iterrows():
        rec_type = str(row["Record Type"]).strip().upper()
        rec_name = str(row["Record Name"]).strip()

        if not rec_type or not rec_name or rec_name.lower() == 'nan':
            continue

        if rec_type not in x_positions:
            current_columns = len(x_positions)
            next_x = START_X + (current_columns * X_SPACING)
            x_positions[rec_type] = str(next_x)
            y_counters[rec_type] = START_Y

            header = ET.SubElement(root, "widget", type="label", version="2.0.0")
            ET.SubElement(header, "name").text = f"Header_{rec_type}"
            ET.SubElement(header, "text").text = rec_type
            ET.SubElement(header, "x").text = str(next_x)
            ET.SubElement(header, "y").text = "30"
            ET.SubElement(header, "width").text = "150"
            ET.SubElement(header, "height").text = "30"
            ET.SubElement(header, "horizontal_alignment").text = "1"
            
            font_element = ET.SubElement(header, "font")
            ET.SubElement(font_element, "font", family="Liberation Sans", size="16", style="BOLD")

        widget = ET.SubElement(root, "widget", type="textupdate", version="2.0.0")
        ET.SubElement(widget, "name").text = f"Monitor_{rec_name.replace(':', '_')}"
        ET.SubElement(widget, "pv_name").text = rec_name

        ET.SubElement(widget, "x").text = x_positions[rec_type]
        ET.SubElement(widget, "y").text = str(y_counters[rec_type])
        ET.SubElement(widget, "width").text = "150"
        ET.SubElement(widget, "height").text = "25"
        ET.SubElement(widget, "horizontal_alignment").text = "1"
        ET.SubElement(widget, "vertical_alignment").text = "1"

        y_counters[rec_type] += Y_SPACING
        widgets_added += 1

    if widgets_added == 0:
        print(f"  -> Warning: No valid records parsed from {excel_path.name}. Skipping file save.")
        return

    max_y = max(y_counters.values()) if y_counters else 1000
    max_x = START_X + (len(x_positions) * X_SPACING) + 50
    root.find("width").text = str(max(int(max_x), 800))
    root.find("height").text = str(max(int(max_y) + 50, 1000))

    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

def process_directory(input_path, output_base_path, folder_modifier=None, is_test=False):
    start_time = time.time()
    input_dir = Path(input_path).resolve()
    base_output = Path(output_base_path).resolve()
    
    if not input_dir.is_dir():
        print(f"Error: Source directory '{input_dir}' does not exist.")
        return

    subdirs = [d for d in input_dir.iterdir() if d.is_dir()]
    total_subdirs_count = len(list(input_dir.rglob('*'))) - len(list(input_dir.rglob('*.xlsx')))

    if is_test:
        has_test_folder = any(d.name.startswith("test_") for d in subdirs)
        if not has_test_folder:
            raise ValueError(
                "\n[ERROR] Test mode validation failed!\n"
                "To run in test mode, your input directory must contain at least one folder "
                "named with the format: 'test_*foldername*' (e.g., test_device1)."
            )
        final_output_root = base_output / "test"
    elif folder_modifier:
        final_output_root = base_output / folder_modifier
    else:
        final_output_root = base_output

    excel_files = list(input_dir.glob('*.xlsx')) + list(input_dir.rglob('*.xlsx'))
    excel_files = sorted(list(set(excel_files)))
    total_files = len(excel_files)

    if total_files == 0:
        print(f"No .xlsx files found in {input_dir} or its subfolders.")
        return
    
    print(f"Found {total_files} Excel file(s). Starting Excel -> Phoebus .bob conversion...\n")
    
    for index, excel_path in enumerate(excel_files, start=1):
        relative_path = excel_path.relative_to(input_dir)
        target_subdir = final_output_root / relative_path.parent
        target_subdir.mkdir(parents=True, exist_ok=True)
        
        prefix = "test_" if is_test else ""
        output_filename = f"{prefix}{excel_path.with_suffix('.bob').name}"
        target_output_path = target_subdir / output_filename
        
        percentage = (index / total_files) * 100
        print(f"[{percentage:.1f}%] Processing file {index} of {total_files}:")
        print(f"  Input:  {excel_path.name}")
        print(f"  Output: {target_output_path}")
        
        try:
             generate_bob(excel_path, target_output_path)
             print("  Status: Successfully converted")
        except (FileNotFoundError, PermissionError) as io_err:
             print(f"  Status: File Access Error - {io_err}")
        except Exception as e:
             print(f"  Status: Unexpected Error - {e}")
        print("-" * 50)
         
    elapsed_time = time.time() - start_time
    
    print("\n" + "="*60)
    print("EXECUTION DETAILS SUMMARY")
    print("="*60)
    print(f"Input Directory:          {input_dir}")
    print(f"Total Subdirectories:     {total_subdirs_count}")
    print(f"Total Files Processed:    {total_files}")
    print(f"Output Root Directory:    {final_output_root}")
    print(f"Test Mode Active:         {is_test}")
    print(f"Total Execution Time:     {elapsed_time:.2f} seconds")
    print("="*60 + "\n")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch convert .xlsx files to Phoebus .bob UI screens")
    
    parser.add_argument("-i", "--source_directory", required=True, 
                        help="Path to directory containing input .xlsx files or folders")
    
    parser.add_argument("-o", "--output_directory", required=True,
                        help="Path to the base directory where output files/folders will be placed")
    
    parser.add_argument("-f", "--folder_name", default=None,
                        help="Optional: Create a specific folder inside the output directory to place files in")
    
    parser.add_argument("-t", "--test", action="store_true", 
                        help="Run in test mode (requires 'test_*' subfolders, creates a 'test/' folder inside -o)")
    
    args = parser.parse_args()
    
    try:
        process_directory(
            input_path=args.source_directory, 
            output_base_path=args.output_directory, 
            folder_modifier=args.folder_name, 
            is_test=args.test
        )
    except ValueError as err:
        print(err)
        sys.exit(1)