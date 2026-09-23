import sys
from os.path import join, dirname

# Upload firmware + LittleFS secara berurutan
Import("env")

def upload_both(source, target, env):
    print("=" * 50)
    print("Step 1/2: Uploading firmware...")
    print("=" * 50)
    env.Execute("pio run --target upload")
    
    print("\n" + "=" * 50)
    print("Step 2/2: Uploading LittleFS data files...")
    print("=" * 50)
    env.Execute("pio run --target uploadfs")
    
    print("\n" + "=" * 50)
    print("Upload complete!")
    print("=" * 50)

# Override default upload
env.Replace(UPLOADCMD=upload_both)