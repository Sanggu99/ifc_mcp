
import os

def check_dwg_version(file_path):
    if not os.path.exists(file_path):
        return "File not found."
    
    try:
        with open(file_path, 'rb') as f:
            header = f.read(6).decode('ascii', errors='ignore')
            
        versions = {
            "AC1032": "AutoCAD 2018/2019/2020",
            "AC1027": "AutoCAD 2013/2014/2015/2016/2017",
            "AC1024": "AutoCAD 2010/2011/2012",
            "AC1021": "AutoCAD 2007/2008/2009",
            "AC1018": "AutoCAD 2004/2005/2006",
            "AC1015": "AutoCAD 2000/2000i/2002",
            "AC1014": "Release 14",
            "AC1012": "Release 13",
            "AC1009": "Release 11/12",
            "AC1006": "Release 10",
        }
        
        version_name = versions.get(header, f"Unknown DWG version ({header})")
        return f"File exists. Version: {version_name}"
    except Exception as e:
        return f"Error reading file: {str(e)}"

file_path = r"c:\Users\SEOP\Desktop\ifc mcp\dwg sample\test.dwg"
print(check_dwg_version(file_path))
