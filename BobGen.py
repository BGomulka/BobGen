#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import csv
from pathlib import Path
import argparse
import time
import xml.etree.ElementTree as ET
import logging

logging.basicConfig(level=logging.WARNING, format='%(message)s')
logger = logging.getLogger(__name__)

def generate_bob(csv_path, output_path):
    try:
        with open(csv_path, mode='r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        logger.error(f"  -> Error loading {csv_path.name}: {e}")
        return False

    root = ET.Element("display", version="2.0.0")
    ET.SubElement(root, "name").text = f"Batch Testing Screen - {csv_path.stem}"
    
    ET.SubElement(root, "width").text = "1200"
    ET.SubElement(root, "height").text = "1200"

    START_X = 50
    X_SPACING = 180
    START_Y = 80
    Y_SPACING = 35

    x_positions = {}
    y_counters = {}
    widgets_added = 0

    for row in rows:
        rec_type = str(row.get("Record Type", "")).strip().upper()
        rec_name = str(row.get("Record Name", "")).strip()

        if not rec_type or not rec_name or rec_name.lower() in ('nan', ''):
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
        logger.warning(f"  -> Warning: No valid records parsed from {csv_path.name}. Skipping file save.")
        return False

    max_y = max(y_counters.values()) if y_counters else 1000
    max_x = START_X + (len(x_positions) * X_SPACING) + 50
    root.find("width").text = str(max(int(max_x), 800))
    root.find("height").text = str(max(int(max_y) + 50, 1000))

    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    return True

def resolve_files(input_path, is_batch, is_test, ext):
    in_p = Path(input_path).resolve() if input_path else Path.cwd()
    files = []
    
    if is_batch:
        if in_p.is_dir():
            files = list(in_p.rglob(f"*{ext}"))
        else:
            logger.error(f"Error: Batch mode requires a directory. '{in_p}' is a file.")
            sys.exit(1)
    else:
        if in_p.is_file() and in_p.suffix == ext:
            files = [in_p]
        elif in_p.is_dir():
            found = list(in_p.glob(f"*{ext}"))
            if found:
                files = [found[0]]
                logger.info(f"Single file mode: Auto-selected first valid file '{files[0].name}'.")
            
    if is_test:
        files = [f for f in files if f.name.lower().startswith("test")]
        if not files:
            logger.error("\n[ERROR] Test mode validation failed! No files starting with 'test' found.")
            sys.exit(1)
            
    return sorted(list(set(files))), in_p

def process_pipeline(args):
    start_time = time.time()
    
    if args.verbose:
        logger.setLevel(logging.INFO)

    input_files, input_dir = resolve_files(args.input, args.batch, args.test, '.csv')
    base_output = Path(args.output).resolve() if args.output else Path.cwd()
    
    if args.test:
        final_output_root = base_output / "test"
    elif args.folder_name:
        final_output_root = base_output / args.folder_name
    else:
        final_output_root = base_output

    total_files = len(input_files)
    if total_files == 0:
        logger.error(f"No valid .csv files found to process.")
        return
    
    logger.info(f"Found {total_files} CSV file(s). Starting CSV -> Phoebus .bob conversion...\n")
    
    success_count = 0
    for index, csv_path in enumerate(input_files, start=1):
        if args.batch:
            relative_path = csv_path.relative_to(input_dir)
            target_subdir = final_output_root / relative_path.parent
        else:
            target_subdir = final_output_root
            
        target_subdir.mkdir(parents=True, exist_ok=True)
        
        output_filename = csv_path.with_suffix('.bob').name
        target_output_path = target_subdir / output_filename
        
        percentage = (index / total_files) * 100
        logger.info(f"[{percentage:.1f}%] Processing file {index} of {total_files}:")
        logger.info(f"  Input:  {csv_path.name}")
        logger.info(f"  Output: {target_output_path}")
        
        try:
            if generate_bob(csv_path, target_output_path):
                logger.info("  Status: Successfully converted")
                success_count += 1
        except (FileNotFoundError, PermissionError) as io_err:
            logger.error(f"  Status: File Access Error - {io_err}")
        except Exception as e:
            logger.error(f"  Status: Unexpected Error - {e}")
            
        logger.info("-" * 50)
         
    if args.verbose:
        elapsed_time = time.time() - start_time
        logger.info("\n" + "="*60)
        logger.info("EXECUTION DETAILS SUMMARY")
        logger.info("="*60)
        logger.info(f"Target Input Path:        {input_dir}")
        logger.info(f"Total Files Processed:    {total_files}")
        logger.info(f"Total Success:            {success_count}")
        logger.info(f"Output Root Directory:    {final_output_root}")
        logger.info(f"Test Mode Active:         {args.test}")
        logger.info(f"Batch Mode Active:        {args.batch}")
        logger.info(f"Total Execution Time:     {elapsed_time:.2f} seconds")
        logger.info("="*60 + "\n")
    
    print("Complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert .csv files to Phoebus .bob UI screens")
    
    parser.add_argument("-i", "--input", default=None, 
                        help="Path to input .csv file or directory (Defaults to Current Working Directory)")
    parser.add_argument("-o", "--output", default=None,
                        help="Path to save output (Defaults to Current Working Directory)")
    parser.add_argument("-b", "--batch", action="store_true",
                        help="Process directories recursively instead of a single file")
    parser.add_argument("-f", "--folder_name", default=None,
                        help="Optional: Create a specific folder inside the output directory to place files in")
    parser.add_argument("-t", "--test", action="store_true", 
                        help="Run in test mode (only processes files starting with 'test')")
    parser.add_argument("-v", "--verbose", action="store_true", 
                        help="Enable detailed logging output")
    
    args = parser.parse_args()
    
    try:
        process_pipeline(args)
    except Exception as err:
        logger.error(err)
        sys.exit(1)