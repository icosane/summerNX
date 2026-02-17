#!/usr/bin/env python3
"""
SAFE EN→JA PORTER FOR .AST FILES (v2 - Block Numbering Aware)
Surgically replaces ONLY ja={...} subsections inside text blocks.
Correctly handles block numbering offset:
  • TO files: block_00000, block_00001, ...
  • FROM files: ["0001_00001"], ["0001_00002"], ...
  • Mapping: block_00000 (TO) ↔ ["0001_00001"] (FROM)
Preserves 100% of game structure - ONLY modifies text/ja sections.
"""
import re
import sys
from pathlib import Path
from typing import List, Tuple, Optional, Dict

class ASTBlock:
    def __init__(self, start: int, end: int, content: str, block_id: int, raw_header: str):
        self.start = start
        self.end = end
        self.content = content
        self.block_id = block_id  # Numeric ID (00000 for block_00000, 00001 for ["0001_00001"], etc.)
        self.raw_header = raw_header  # Original header text (for reconstruction)

class ASTProcessor:
    def __init__(self):
        self.mismatched_files: List[Tuple[str, int, int, List[int]]] = []  # (filename, to_count, from_count, unmatched_ids)
        self.failed_files: List[Tuple[str, str]] = []  # (filename, error_msg)
        self.successful_files: List[str] = []

    def find_matching_brace(self, text: str, start_idx: int) -> int:
        """Find position after matching closing brace with proper nesting."""
        if start_idx >= len(text) or text[start_idx] != '{':
            return -1
        
        depth = 1
        i = start_idx + 1
        while i < len(text) and depth > 0:
            # Skip escaped braces
            if i > 0 and text[i-1] == '\\':
                i += 1
                continue
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
            i += 1
        
        return i if depth == 0 else -1

    def extract_blocks_to(self, content: str) -> List[ASTBlock]:
        """Extract blocks from TO file (block_00000 format)."""
        blocks = []
        pos = 0
        block_pattern = r'block_(\d+)\s*=\s*\{'
        
        while pos < len(content):
            match = re.search(block_pattern, content[pos:], re.IGNORECASE)
            if not match:
                break
            
            abs_start = pos + match.start()
            block_id = int(match.group(1))
            brace_pos = pos + match.end() - 1  # Position of '{'
            
            # Find matching closing brace for the entire block
            end_pos = self.find_matching_brace(content, brace_pos)
            if end_pos == -1:
                pos += match.end()
                continue
            
            # Extract full block content including header
            header_end = pos + match.end()
            full_block = content[abs_start:end_pos]
            blocks.append(ASTBlock(abs_start, end_pos, full_block, block_id, match.group(0)))
            pos = end_pos
        
        return blocks

    def extract_blocks_from(self, content: str) -> List[ASTBlock]:
        """Extract blocks from FROM file (["0001_00001"] format)."""
        blocks = []
        pos = 0
        block_pattern = r'\["\d+_(\d+)"\]\s*=\s*\{'
        
        while pos < len(content):
            match = re.search(block_pattern, content[pos:], re.IGNORECASE)
            if not match:
                break
            
            abs_start = pos + match.start()
            block_id = int(match.group(1))
            brace_pos = pos + match.end() - 1  # Position of '{'
            
            # Find matching closing brace for the entire block
            end_pos = self.find_matching_brace(content, brace_pos)
            if end_pos == -1:
                pos += match.end()
                continue
            
            # Extract full block content including header
            header_end = pos + match.end()
            full_block = content[abs_start:end_pos]
            blocks.append(ASTBlock(abs_start, end_pos, full_block, block_id, match.group(0)))
            pos = end_pos
        
        return blocks

    def extract_ja_section(self, block_content: str) -> Optional[Tuple[int, int, str]]:
        """Extract ja = { ... } subsection from block's text section."""
        # Find 'text = {' first
        text_match = re.search(r'text\s*=\s*\{', block_content, re.IGNORECASE)
        if not text_match:
            return None
        
        text_start = text_match.start()
        brace_pos = text_match.end() - 1
        text_end = self.find_matching_brace(block_content, brace_pos)
        if text_end == -1:
            return None
        
        text_section = block_content[text_start:text_end]
        
        # Find 'ja = {' inside text section
        ja_match = re.search(r'ja\s*=\s*\{', text_section, re.IGNORECASE)
        if not ja_match:
            return None
        
        ja_start_in_section = ja_match.start()
        brace_pos = ja_match.end() - 1
        ja_end_in_section = self.find_matching_brace(text_section, brace_pos)
        if ja_end_in_section == -1:
            return None
        
        ja_content = text_section[ja_start_in_section:ja_end_in_section]
        abs_start = text_start + ja_start_in_section
        abs_end = text_start + ja_end_in_section
        
        return (abs_start, abs_end, ja_content)

    def extract_en_section(self, block_content: str) -> Optional[str]:
        """Extract and transform en = { ... } subsection from FROM block."""
        # Find 'text = {' first
        text_match = re.search(r'text\s*=\s*\{', block_content, re.IGNORECASE)
        if not text_match:
            return None
        
        text_start = text_match.start()
        brace_pos = text_match.end() - 1
        text_end = self.find_matching_brace(block_content, brace_pos)
        if text_end == -1:
            return None
        
        text_section = block_content[text_start:text_end]
        
        # Find 'en = {' inside text section
        en_match = re.search(r'en\s*=\s*\{', text_section, re.IGNORECASE)
        if not en_match:
            return None
        
        en_start = en_match.start()
        brace_pos = en_match.end() - 1
        en_end = self.find_matching_brace(text_section, brace_pos)
        if en_end == -1:
            return None
        
        en_content = text_section[en_start:en_end]
        
        # Transform name fields: keep only last element (English name)
        def transform_name(match):
            # Extract all quoted strings in the array
            strings = re.findall(r'"(?:[^"\\]|\\.)*"', match.group(2))
            if strings:
                return f'{match.group(1)}{strings[-1]}{match.group(3)}'
            return match.group(0)
        
        en_content = re.sub(
            r'(name\s*=\s*\{)(.*?)(\})',
            transform_name,
            en_content,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # Change 'en =' to 'ja =' at start
        en_content = re.sub(r'^en\s*=', 'ja =', en_content, count=1, flags=re.IGNORECASE)
        return en_content

    def process_file(self, to_path: Path, from_path: Path, out_path: Path) -> bool:
        """Process a single file pair with block-aware matching."""
        try:
            # Read files with UTF-8 encoding
            to_content = to_path.read_text(encoding='utf-8')
            from_content = from_path.read_text(encoding='utf-8')
            
            # Extract blocks from both files
            to_blocks = self.extract_blocks_to(to_content)
            from_blocks = self.extract_blocks_from(from_content)
            
            if not to_blocks:
                self.failed_files.append((to_path.name, "No blocks found in TO file"))
                return False
            
            if not from_blocks:
                self.failed_files.append((to_path.name, "No blocks found in FROM file"))
                return False
            
            # Create lookup dictionaries by block ID
            to_blocks_dict = {b.block_id: b for b in to_blocks}
            from_blocks_dict = {b.block_id: b for b in from_blocks}
            
            # Match blocks: TO block_id N ↔ FROM block_id N+1
            # Example: block_00000 (ID=0) ↔ ["0001_00001"] (ID=1)
            replacements = {}
            unmatched_to = []
            unmatched_from = []
            
            for to_id, to_block in to_blocks_dict.items():
                from_id = to_id + 1  # Offset correction
                if from_id in from_blocks_dict:
                    en_section = self.extract_en_section(from_blocks_dict[from_id].content)
                    if en_section:
                        ja_pos = self.extract_ja_section(to_block.content)
                        if ja_pos:
                            replacements[to_block.start + ja_pos[0]] = (to_block.start + ja_pos[1], en_section)
                        else:
                            unmatched_to.append(to_id)
                else:
                    unmatched_to.append(to_id)
            
            for from_id in from_blocks_dict:
                if (from_id - 1) not in to_blocks_dict:
                    unmatched_from.append(from_id)
            
            # Report mismatches if any
            if unmatched_to or unmatched_from:
                self.mismatched_files.append((
                    to_path.name,
                    len(to_blocks),
                    len(from_blocks),
                    unmatched_to + unmatched_from
                ))
                print(f"  ⚠ Block mismatch: {len(unmatched_to)} TO blocks unmatched, {len(unmatched_from)} FROM blocks unmatched")
            
            if not replacements:
                self.failed_files.append((to_path.name, "No valid replacements found"))
                return False
            
            # Apply replacements from END to START to avoid position shifting
            result_chars = list(to_content)
            for start_pos in sorted(replacements.keys(), reverse=True):
                end_pos, replacement = replacements[start_pos]
                result_chars[start_pos:end_pos] = list(replacement)
            
            result = ''.join(result_chars)
            
            # Safety check: verify basic AST structure remains intact
            if 'astver' not in result[:200] or 'ast = {' not in result[:300]:
                self.failed_files.append((to_path.name, "CRITICAL: Output structure corrupted (missing astver/ast)"))
                return False
            
            # Ensure output directory exists
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write result
            out_path.write_text(result, encoding='utf-8')
            self.successful_files.append(to_path.name)
            return True
            
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)[:150]}"
            self.failed_files.append((to_path.name, error_msg))
            print(f"  ✗ ERROR: {error_msg}")
            import traceback
            traceback.print_exc()
            return False

    def write_reports(self, output_folder: Path):
        """Write detailed reports for mismatches and failures."""
        # Mismatch report
        if self.mismatched_files:
            mismatch_path = output_folder / "BLOCK_MISMATCH_REPORT.txt"
            with open(mismatch_path, 'w', encoding='utf-8') as f:
                f.write("FILES WITH BLOCK NUMBERING MISMATCHES\n")
                f.write("=" * 70 + "\n")
                f.write(f"{'Filename':<40} {'TO Blocks':<12} {'FROM Blocks':<12} {'Unmatched IDs'}\n")
                f.write("-" * 70 + "\n")
                for filename, to_count, from_count, unmatched in self.mismatched_files:
                    unmatched_str = ','.join(str(u) for u in unmatched[:5]) + ('...' if len(unmatched) > 5 else '')
                    f.write(f"{filename:<40} {to_count:<12} {from_count:<12} {unmatched_str}\n")
                f.write("=" * 70 + "\n")
                f.write(f"\nTotal mismatched files: {len(self.mismatched_files)}\n")
            print(f"\n⚠ Block mismatch report saved to: {mismatch_path.resolve()}")
        
        # Failure report
        if self.failed_files:
            failure_path = output_folder / "PROCESSING_FAILURE_REPORT.txt"
            with open(failure_path, 'w', encoding='utf-8') as f:
                f.write("FILES THAT FAILED TO PROCESS\n")
                f.write("=" * 70 + "\n")
                f.write(f"{'Filename':<40} {'Error'}\n")
                f.write("-" * 70 + "\n")
                for filename, error in self.failed_files:
                    f.write(f"{filename:<40} {error}\n")
                f.write("=" * 70 + "\n")
                f.write(f"\nTotal failed files: {len(self.failed_files)}\n")
            print(f"✗ Failure report saved to: {failure_path.resolve()}")
        
        # Success summary
        summary_path = output_folder / "PROCESSING_SUMMARY.txt"
        total_files = len(self.successful_files) + len(self.failed_files)
        with open(summary_path, 'w', encoding='utf-8') as f:
            f.write("PROCESSING SUMMARY\n")
            f.write("=" * 70 + "\n")
            f.write(f"Total files processed:    {total_files}\n")
            f.write(f"Successfully processed:   {len(self.successful_files)}\n")
            f.write(f"Block mismatches:         {len(self.mismatched_files)}\n")
            f.write(f"Processing failures:      {len(self.failed_files)}\n")
            f.write("=" * 70 + "\n\n")
            
            if self.successful_files:
                f.write("Successfully processed files:\n")
                for fname in sorted(self.successful_files):
                    f.write(f"  • {fname}\n")
            
            if self.mismatched_files:
                f.write("\nFiles with block mismatches:\n")
                for fname, _, _, _ in sorted(self.mismatched_files):
                    f.write(f"  • {fname}\n")
            
            if self.failed_files:
                f.write("\nFailed files:\n")
                for fname, _ in sorted(self.failed_files):
                    f.write(f"  • {fname}\n")
        
        print(f"✅ Summary saved to: {summary_path.resolve()}")

def main():
    if len(sys.argv) != 4:
        script_name = Path(sys.argv[0]).name
        print(f"Usage: python {script_name} <to_folder> <from_folder> <output_folder>")
        print("\nExample:")
        print(f"  python {script_name} \"C:/game/to\" \"C:/game/from\" \"C:/game/output\"")
        print("\nThis script:")
        print("  • Correctly handles block numbering offset (block_00000 ↔ [\"0001_00001\"])")
        print("  • Replaces ONLY ja={...} subsections inside text blocks")
        print("  • Transforms name fields: {\"遥斗\", \"Haruto\"} → {\"Haruto\"}")
        print("  • Preserves 100% of game commands, metadata, and file structure")
        print("  • Outputs detailed reports for mismatches/failures")
        sys.exit(1)
    
    to_folder = Path(sys.argv[1])
    from_folder = Path(sys.argv[2])
    out_folder = Path(sys.argv[3])
    
    # Validate folders
    for folder, name in [(to_folder, "TO"), (from_folder, "FROM")]:
        if not folder.exists():
            print(f"✗ Error: {name} folder does not exist: {folder}")
            sys.exit(1)
        if not folder.is_dir():
            print(f"✗ Error: {name} path is not a directory: {folder}")
            sys.exit(1)
    
    # Get all .ast files
    to_files = sorted([
        f for f in to_folder.iterdir() 
        if f.is_file() and f.suffix.lower() == '.ast'
    ])
    
    if not to_files:
        print(f"✗ No .ast files found in {to_folder}")
        sys.exit(1)
    
    print(f"📁 Processing {len(to_files)} .ast files...")
    print(f"   TO folder:   {to_folder.resolve()}")
    print(f"   FROM folder: {from_folder.resolve()}")
    print(f"   Output to:   {out_folder.resolve()}\n")
    
    processor = ASTProcessor()
    success_count = 0
    
    for to_path in to_files:
        from_path = from_folder / to_path.name
        out_path = out_folder / to_path.name
        
        print(f"📄 {to_path.name}", end=' ')
        
        if not from_path.exists():
            processor.failed_files.append((to_path.name, "No matching file in FROM folder"))
            print("→ ✗ MISSING FROM FILE")
            continue
        
        if processor.process_file(to_path, from_path, out_path):
            print("→ ✓ OK")
            success_count += 1
        else:
            print("→ ✗ FAILED")
    
    # Final summary
    print("\n" + "="*70)
    print("✅ PROCESSING COMPLETE")
    print("="*70)
    print(f"   Success:     {success_count}")
    print(f"   Mismatches:  {len(processor.mismatched_files)}")
    print(f"   Failed:      {len(processor.failed_files)}")
    print(f"   Output:      {out_folder.resolve()}")
    print("="*70)
    
    # Write reports
    processor.write_reports(out_folder)
    
    if processor.failed_files:
        print("\n⚠ Some files failed - check PROCESSING_FAILURE_REPORT.txt")
    if processor.mismatched_files:
        print("⚠ Some files had block mismatches - check BLOCK_MISMATCH_REPORT.txt")
    
    # Exit with appropriate code
    sys.exit(0 if success_count > 0 else 1)

if __name__ == "__main__":
    main()