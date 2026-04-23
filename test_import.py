#!/usr/bin/env python3
try:
    import main
    print("main.py imported successfully")
    print(f"App object: {main.app}")
except Exception as e:
    print(f"Error importing main: {e}")
    import traceback
    traceback.print_exc()
