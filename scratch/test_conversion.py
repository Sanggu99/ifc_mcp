
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(r"c:\Users\SEOP\Desktop\ifc mcp\backend")
sys.path.append(str(backend_dir))

from services.dxf_parser import parse_dxf
from services.ifc_builder import build_ifc_from_dxf

def run_test_conversion():
    input_file = backend_dir / "uploads" / "test.dxf"
    output_file = backend_dir / "outputs" / "test.ifc"
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    print(f"Starting conversion: {input_file}")
    
    try:
        # Step 1: Parse
        parse_result = parse_dxf(str(input_file))
        print(f"Parsed {len(parse_result.lines)} lines, {len(parse_result.polylines)} polylines.")
        print(f"Detected layers: {list(parse_result.layers.keys())}")
        
        # Step 2: Build IFC
        # User requested 3000mm wall height -> 3.0m
        stats = build_ifc_from_dxf(
            parse_result=parse_result,
            output_path=str(output_file),
            wall_height=3.0,
            wall_thickness=0.2,
            project_name="Updated Wall Layer Test"
        )
        
        print("\nConversion Results:")
        for key, val in stats.items():
            print(f"  {key}: {val}")
            
        if os.path.exists(output_file):
            print(f"\nSuccess! IFC file created at: {output_file}")
            print(f"File size: {os.path.getsize(output_file)} bytes")
        else:
            print("\nError: IFC file was not created.")
            
    except Exception as e:
        import traceback
        print(f"\nAn error occurred during conversion: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    run_test_conversion()
