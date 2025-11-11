#!/usr/bin/env python3
"""
CSP .sut File Validator

This script validates a .sut file to ensure it meets CSP requirements
before attempting to import it into Clip Studio Paint.

Usage:
    python3 validate_sut.py <file.sut>
"""

import sqlite3
import sys
import os

def validate_sut_file(filepath):
    """Validate a .sut file for CSP compatibility."""
    
    print(f"🔍 Validating: {filepath}")
    print("=" * 60)
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    try:
        conn = sqlite3.connect(filepath)
        cursor = conn.cursor()
        
        # Check page size
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]
        if page_size == 1024:
            print(f"✅ Page size: {page_size} (correct)")
        else:
            print(f"❌ Page size: {page_size} (should be 1024)")
            return False
        
        # Check encoding
        cursor.execute("PRAGMA encoding")
        encoding = cursor.fetchone()[0]
        if encoding == "UTF-8":
            print(f"✅ Encoding: {encoding} (correct)")
        else:
            print(f"⚠️  Encoding: {encoding} (expected UTF-8)")
        
        # Check integrity
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        if integrity == "ok":
            print(f"✅ Integrity check: {integrity}")
        else:
            print(f"❌ Integrity check failed: {integrity}")
            return False
        
        print("\n📋 Table Structure:")
        print("-" * 60)
        
        # Check required tables
        required_tables = ['Manager', 'Node', 'Variant', 'MaterialFile']
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in required_tables:
            if table in tables:
                print(f"✅ Table '{table}' exists")
            else:
                print(f"❌ Table '{table}' missing")
                return False
        
        print("\n📊 Data Validation:")
        print("-" * 60)
        
        # Validate Manager table
        cursor.execute("SELECT _PW_ID, ToolType, Version, RootUuid, MaxVariantID, SavedCount FROM Manager")
        manager = cursor.fetchone()
        if manager:
            print(f"✅ Manager record found")
            print(f"   - _PW_ID: {manager[0]}")
            print(f"   - ToolType: {manager[1]} {'✅' if manager[1] == 0 else '⚠️ (expected 0)'}")
            print(f"   - Version: {manager[2]} {'✅' if manager[2] == 126 else '⚠️ (expected 126)'}")
            print(f"   - RootUuid: {'Set ✅' if manager[3] else 'NULL ❌'}")
            print(f"   - MaxVariantID: {manager[4]}")
            print(f"   - SavedCount: {manager[5]}")
            
            root_uuid = manager[3]
        else:
            print("❌ No Manager record found")
            return False
        
        # Validate Node table
        cursor.execute("SELECT COUNT(*) FROM Node")
        node_count = cursor.fetchone()[0]
        print(f"\n✅ Node records: {node_count}")
        
        # Check root node
        cursor.execute("SELECT _PW_ID, NodeUuid, NodeName, NodeFirstChildUuid FROM Node WHERE _PW_ID = 1")
        root_node = cursor.fetchone()
        if root_node:
            print(f"   Root Node:")
            print(f"   - _PW_ID: {root_node[0]}")
            print(f"   - NodeName: {root_node[2]}")
            print(f"   - NodeUuid matches RootUuid: {'✅' if root_node[1] == root_uuid else '❌'}")
            print(f"   - NodeFirstChildUuid: {'Set ✅' if root_node[3] else 'NULL ⚠️'}")
            
            first_child_uuid = root_node[3]
        else:
            print("❌ Root node not found")
            return False
        
        # Check brush nodes
        cursor.execute("SELECT _PW_ID, NodeUuid, NodeName, NodeVariantID, NodeInitVariantID FROM Node WHERE _PW_ID > 1")
        brush_nodes = cursor.fetchall()
        print(f"\n   Brush Nodes: {len(brush_nodes)}")
        for node in brush_nodes:
            print(f"   - {node[2]} (ID: {node[0]})")
            print(f"     NodeVariantID: {node[3]} {'✅' if node[3] else '❌'}")
            print(f"     NodeInitVariantID: {node[4]} {'✅' if node[4] else '❌'}")
        
        # Validate Variant table
        cursor.execute("SELECT COUNT(*) FROM Variant")
        variant_count = cursor.fetchone()[0]
        print(f"\n✅ Variant records: {variant_count}")
        
        cursor.execute("""
            SELECT VariantID, Opacity, AntiAlias, CompositeMode, 
                   BrushSize, BrushSizeUnit, BrushHardness, BrushInterval,
                   BrushUsePatternImage, BrushPatternImageArray
            FROM Variant
        """)
        variants = cursor.fetchall()
        for variant in variants:
            print(f"   Variant ID: {variant[0]}")
            print(f"   - Opacity: {variant[1]} {'✅' if 0 <= variant[1] <= 100 else '❌'}")
            print(f"   - AntiAlias: {variant[2]}")
            print(f"   - CompositeMode: {variant[3]}")
            print(f"   - BrushSize: {variant[4]}")
            print(f"   - BrushSizeUnit: {variant[5]}")
            print(f"   - BrushHardness: {variant[6]} {'✅' if 0 <= variant[6] <= 100 else '❌'}")
            print(f"   - BrushInterval: {variant[7]}")
            print(f"   - BrushUsePatternImage: {variant[8]}")
            print(f"   - BrushPatternImageArray: {'Set ✅' if variant[9] else 'NULL ⚠️'}")
        
        print("\n🔗 Foreign Key Validation:")
        print("-" * 60)
        
        # Check Manager.RootUuid = Root Node.NodeUuid
        cursor.execute("SELECT RootUuid FROM Manager")
        manager_root = cursor.fetchone()[0]
        cursor.execute("SELECT NodeUuid FROM Node WHERE _PW_ID = 1")
        node_root = cursor.fetchone()[0]
        if manager_root == node_root:
            print("✅ Manager.RootUuid matches Root Node.NodeUuid")
        else:
            print("❌ Manager.RootUuid does NOT match Root Node.NodeUuid")
            return False
        
        # Check Node.NodeVariantID references exist in Variant
        cursor.execute("SELECT NodeVariantID FROM Node WHERE NodeVariantID IS NOT NULL")
        node_variants = [row[0] for row in cursor.fetchall()]
        cursor.execute("SELECT VariantID FROM Variant")
        variant_ids = [row[0] for row in cursor.fetchall()]
        
        all_valid = True
        for nv in node_variants:
            if nv in variant_ids:
                print(f"✅ Node.NodeVariantID {nv} exists in Variant table")
            else:
                print(f"❌ Node.NodeVariantID {nv} NOT found in Variant table")
                all_valid = False
        
        if not all_valid:
            return False
        
        # Check MaxVariantID
        cursor.execute("SELECT MaxVariantID FROM Manager")
        max_variant_id = cursor.fetchone()[0]
        cursor.execute("SELECT MAX(VariantID) FROM Variant")
        actual_max = cursor.fetchone()[0]
        if max_variant_id >= actual_max:
            print(f"✅ Manager.MaxVariantID ({max_variant_id}) >= max Variant.VariantID ({actual_max})")
        else:
            print(f"⚠️  Manager.MaxVariantID ({max_variant_id}) < max Variant.VariantID ({actual_max})")
        
        conn.close()
        
        print("\n" + "=" * 60)
        print("✅ Validation PASSED - File should be compatible with CSP")
        print("=" * 60)
        return True
        
    except sqlite3.Error as e:
        print(f"❌ SQLite error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python validate_sut.py <file.sut>")
        print("\nExample:")
        print("  python validate_sut.py test_minimal.sut")
        sys.exit(1)
    
    filepath = sys.argv[1]
    success = validate_sut_file(filepath)
    
    if success:
        print("\n✅ Ready to import into Clip Studio Paint!")
        sys.exit(0)
    else:
        print("\n❌ File has issues - fix before importing into CSP")
        sys.exit(1)

if __name__ == "__main__":
    main()
