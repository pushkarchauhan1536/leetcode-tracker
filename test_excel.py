# test_excel.py
import pandas as pd

try:
    df = pd.read_excel('students.xlsx')
    print(f"✅ Excel file loaded successfully!")
    print(f"📊 Columns found: {list(df.columns)}")
    print(f"📈 Total students: {len(df)}")
    print(f"\n📝 First 3 rows:")
    print(df.head(3))
    
    # Check required columns
    required = ['roll', 'name', 'leetcode_ids']
    missing = [col for col in required if col not in df.columns]
    
    if missing:
        print(f"\n❌ Missing columns: {missing}")
        print(f"   Your columns: {list(df.columns)}")
    else:
        print(f"\n✅ All required columns found!")
        
except FileNotFoundError:
    print(f"❌ students.xlsx not found in current directory")
    print(f"Current directory: {os.getcwd()}")
except Exception as e:
    print(f"❌ Error: {e}")