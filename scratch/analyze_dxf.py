
import ezdxf
import os
import sys

# Add backend to path to use existing services if needed
sys.path.append(r"c:\Users\SEOP\Desktop\ifc mcp\backend")

def analyze_dxf(file_path):
    if not os.path.exists(file_path):
        return f"Error: File not found at {file_path}"
    
    try:
        doc = ezdxf.readfile(file_path)
        msp = doc.modelspace()
        
        # 1. Summary of entities
        stats = {}
        for entity in msp:
            dxftype = entity.dxftype()
            stats[dxftype] = stats.get(dxftype, 0) + 1
            
        # 2. Layers
        layers = [layer.dxf.name for layer in doc.layers]
        
        # 3. Unit check
        insunits = doc.header.get("$INSUNITS", 0)
        unit_names = {
            0: "Unitless", 1: "Inches", 2: "Feet", 4: "Millimeters", 
            5: "Centimeters", 6: "Meters"
        }
        unit_str = unit_names.get(insunits, f"Other ({insunits})")

        print(f"--- DXF Analysis: {os.path.basename(file_path)} ---")
        print(f"Unit Setting: {unit_str}")
        print("\nEntity Counts:")
        for etype, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            print(f"  - {etype}: {count}")
            
        print("\nLayers Found:")
        for layer in sorted(layers):
            print(f"  - {layer}")
            
        return "Analysis complete."
    except Exception as e:
        return f"Error reading DXF: {str(e)}"

file_path = r"c:\Users\SEOP\Desktop\ifc mcp\dwg sample\test.dxf"
analyze_dxf(file_path)
