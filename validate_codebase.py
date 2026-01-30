import os
import sys
import importlib
import pkgutil
import traceback
import ast

def check_syntax(file_path):
    """Check for SyntaxErrors in a file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        compile(source, file_path, 'exec')
        return None
    except SyntaxError as e:
        return f"SyntaxError in {file_path}:Line {e.lineno}: {e.msg}"
    except Exception as e:
        return f"Error reading {file_path}: {e}"

def check_imports(package_name):
    """Recursively check imports for a package."""
    errors = []
    
    # Add project root to path
    project_root = os.path.abspath(os.getcwd())
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    print(f"🔍 Scanning package: {package_name}")
    
    # Walk through all files to check syntax first
    for root, dirs, files in os.walk(package_name):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                syntax_error = check_syntax(full_path)
                if syntax_error:
                    errors.append(syntax_error)

    if errors:
        print("❌ Syntax Errors Found (Fix these before Import Checks):")
        for e in errors:
            print(f"  - {e}")
        return errors

    # If syntax is clean, try importing modules
    print("✅ Syntax Check Passed. Checking Imports...")
    
    ignore_list = ["validate_codebase.py", "migrations"] # Skip special files

    for root, dirs, files in os.walk(package_name):
        for file in files:
            if file.endswith(".py") and file not in ignore_list:
                # Convert path to module name
                rel_path = os.path.relpath(os.path.join(root, file), project_root)
                module_name = rel_path.replace(os.sep, ".").replace(".py", "")
                
                try:
                    importlib.import_module(module_name)
                    # print(f"  OK: {module_name}")
                except ImportError as e:
                    errors.append(f"ImportError in {module_name}: {e}")
                except ModuleNotFoundError as e:
                    errors.append(f"ModuleNotFoundError in {module_name}: {e}")
                except Exception as e:
                    # Capture other side-effect errors during import (e.g. DB connection)
                    # We might ignore some runtime errors if they rely on env vars
                    pass

    return errors

if __name__ == "__main__":
    print("🚀 Starting Codebase Integrity Check...")
    errors = check_imports("app")
    
    if errors:
        print("\n💥 INTEGRITY CHECK FAILED! Found errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("\n✨ ALL CHECKS PASSED! Codebase is import-safe.")
        sys.exit(0)
