import sys
import os
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(r"c:\Users\SEOP\Desktop\ifc mcp\backend")))

import ifcopenshell
from services.ifc_builder import create_ifc_project, create_wall_from_line, Point3D

def test_wall_creation():
    try:
        print("Creating project...")
        model, project, site, building, storey, body_context = create_ifc_project()
        
        print("Creating wall...")
        start = Point3D(0, 0, 0)
        end = Point3D(5, 0, 0)
        wall = create_wall_from_line(model, storey, body_context, start, end)
        
        if wall:
            print(f"Wall created: {wall.GlobalId}")
            output_path = "test_output.ifc"
            model.write(output_path)
            print(f"Saved to {output_path}")
        else:
            print("Wall creation failed: returned None")
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Error: {e}")

if __name__ == "__main__":
    test_wall_creation()
