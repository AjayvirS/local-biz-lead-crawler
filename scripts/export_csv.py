"""
Export crawled leads to CSV format.

Converts stored lead data to CSV for easy analysis.
"""

import csv
import json


def export_to_csv(input_file, output_file):
    """
    Export leads from JSON to CSV format.
    
    Args:
        input_file: Path to the input JSON file
        output_file: Path to the output CSV file
    """
    # TODO: Implement CSV export
    print(f"Exporting leads from {input_file} to {output_file}...")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 3:
        print("Usage: python export_csv.py <input_json> <output_csv>")
        sys.exit(1)
    
    export_to_csv(sys.argv[1], sys.argv[2])
