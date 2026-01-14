"""
Privacy-First Data Ingestor
Memory-efficient data loading with Generator pattern for 8GB RAM optimization
Supports JSON, CSV, TXT with auto-encoding detection
"""

import json
import csv
import chardet
from typing import Generator, Dict, Any, List
from pathlib import Path
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import PRIVACY_CHUNK_SIZE

# Try to import optional dependencies
try:
    import ijson
    IJSON_AVAILABLE = True
except ImportError:
    IJSON_AVAILABLE = False
    print("⚠️  ijson not installed. Using fallback JSON parser.")

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    print("⚠️  pandas not installed. Using fallback CSV parser.")


class PrivacyIngestor:
    """
    Memory-efficient data ingestor for Privacy Mode
    Uses generators to process large files without loading entire file into memory
    """
    
    def __init__(self, chunk_size: int = PRIVACY_CHUNK_SIZE):
        """
        Initialize ingestor
        
        Args:
            chunk_size: Maximum characters per chunk for text processing
        """
        self.chunk_size = chunk_size
        self.supported_formats = ['.json', '.csv', '.txt', '.tsv']
    
    def detect_encoding(self, filepath: str) -> str:
        """
        Detect file encoding (UTF-8, EUC-KR, CP949, etc.)
        
        Args:
            filepath: Path to file
            
        Returns:
            Detected encoding name
        """
        with open(filepath, 'rb') as f:
            raw_data = f.read(10000)  # Read first 10KB for detection
            result = chardet.detect(raw_data)
            encoding = result['encoding'] or 'utf-8'
            confidence = result['confidence']
            
            if confidence < 0.7:
                print(f"⚠️  Low encoding confidence ({confidence:.2f}). Trying UTF-8...")
                encoding = 'utf-8'
            
            print(f"📝 Detected encoding: {encoding} (confidence: {confidence:.2f})")
            return encoding
    
    def ingest_file(self, filepath: str) -> Generator[Dict[str, Any], None, None]:
        """
        Main entry point: Auto-detect format and stream data
        
        Args:
            filepath: Path to data file
            
        Yields:
            Dict with unified schema: {"text": str, "metadata": dict}
        """
        path = Path(filepath)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        suffix = path.suffix.lower()
        
        if suffix not in self.supported_formats:
            raise ValueError(f"Unsupported format: {suffix}. Supported: {self.supported_formats}")
        
        print(f"📂 Ingesting {path.name} ({suffix})...")
        
        if suffix == '.json':
            yield from self._ingest_json_streaming(filepath)
        elif suffix in ['.csv', '.tsv']:
            yield from self._ingest_csv_chunked(filepath)
        else:  # .txt
            yield from self._ingest_txt_lines(filepath)
    
    def _ingest_json_streaming(self, filepath: str) -> Generator[Dict[str, Any], None, None]:
        """
        Stream JSON file using ijson for memory efficiency
        Handles both JSON objects and arrays
        
        Args:
            filepath: Path to JSON file
            
        Yields:
            Parsed JSON chunks with metadata
        """
        encoding = self.detect_encoding(filepath)
        
        if IJSON_AVAILABLE:
            # Use ijson for true streaming (ideal for large files)
            try:
                with open(filepath, 'r', encoding=encoding) as f:
                    # Try to parse as array first
                    parser = ijson.items(f, 'item')
                    count = 0
                    for item in parser:
                        count += 1
                        yield {
                            "text": json.dumps(item, ensure_ascii=False),
                            "metadata": {
                                "source": filepath,
                                "format": "json",
                                "index": count,
                                "type": type(item).__name__
                            }
                        }
            except ijson.JSONError:
                # If not array, parse as single object
                with open(filepath, 'r', encoding=encoding) as f:
                    data = json.load(f)
                    yield {
                        "text": json.dumps(data, ensure_ascii=False),
                        "metadata": {
                            "source": filepath,
                            "format": "json",
                            "index": 0,
                            "type": "object"
                        }
                    }
        else:
            # Fallback: Load entire file (not ideal for large files)
            with open(filepath, 'r', encoding=encoding) as f:
                data = json.load(f)
                
                if isinstance(data, list):
                    for idx, item in enumerate(data):
                        yield {
                            "text": json.dumps(item, ensure_ascii=False),
                            "metadata": {
                                "source": filepath,
                                "format": "json",
                                "index": idx,
                                "type": type(item).__name__
                            }
                        }
                else:
                    yield {
                        "text": json.dumps(data, ensure_ascii=False),
                        "metadata": {
                            "source": filepath,
                            "format": "json",
                            "index": 0,
                            "type": "object"
                        }
                    }
    
    def _ingest_csv_chunked(self, filepath: str) -> Generator[Dict[str, Any], None, None]:
        """
        Stream CSV file in chunks for memory efficiency
        
        Args:
            filepath: Path to CSV file
            
        Yields:
            CSV rows as text with metadata
        """
        encoding = self.detect_encoding(filepath)
        delimiter = '\t' if filepath.endswith('.tsv') else ','
        
        if PANDAS_AVAILABLE:
            # Use pandas with chunksize for efficient streaming
            chunk_iter = pd.read_csv(
                filepath,
                encoding=encoding,
                delimiter=delimiter,
                chunksize=100,  # Process 100 rows at a time
                on_bad_lines='skip'
            )
            
            chunk_idx = 0
            for chunk_df in chunk_iter:
                chunk_idx += 1
                
                # Convert chunk to text representation
                text_parts = []
                text_parts.append(f"Columns: {', '.join(chunk_df.columns)}")
                
                for idx, row in chunk_df.iterrows():
                    row_text = " | ".join([f"{col}: {val}" for col, val in row.items()])
                    text_parts.append(row_text)
                
                yield {
                    "text": "\n".join(text_parts),
                    "metadata": {
                        "source": filepath,
                        "format": "csv",
                        "chunk_index": chunk_idx,
                        "rows": len(chunk_df),
                        "columns": list(chunk_df.columns)
                    }
                }
        else:
            # Fallback: Use standard csv module
            with open(filepath, 'r', encoding=encoding, newline='') as f:
                reader = csv.DictReader(f, delimiter=delimiter)
                
                batch = []
                batch_size = 100
                batch_idx = 0
                
                for row_idx, row in enumerate(reader):
                    batch.append(row)
                    
                    if len(batch) >= batch_size:
                        batch_idx += 1
                        text_parts = []
                        text_parts.append(f"Columns: {', '.join(row.keys())}")
                        
                        for item in batch:
                            row_text = " | ".join([f"{k}: {v}" for k, v in item.items()])
                            text_parts.append(row_text)
                        
                        yield {
                            "text": "\n".join(text_parts),
                            "metadata": {
                                "source": filepath,
                                "format": "csv",
                                "chunk_index": batch_idx,
                                "rows": len(batch),
                                "columns": list(row.keys())
                            }
                        }
                        batch = []
                
                # Yield remaining rows
                if batch:
                    batch_idx += 1
                    text_parts = []
                    text_parts.append(f"Columns: {', '.join(batch[0].keys())}")
                    
                    for item in batch:
                        row_text = " | ".join([f"{k}: {v}" for k, v in item.items()])
                        text_parts.append(row_text)
                    
                    yield {
                        "text": "\n".join(text_parts),
                        "metadata": {
                            "source": filepath,
                            "format": "csv",
                            "chunk_index": batch_idx,
                            "rows": len(batch),
                            "columns": list(batch[0].keys())
                        }
                    }
    
    def _ingest_txt_lines(self, filepath: str) -> Generator[Dict[str, Any], None, None]:
        """
        Stream text file line by line, grouping into chunks
        
        Args:
            filepath: Path to text file
            
        Yields:
            Text chunks with metadata
        """
        encoding = self.detect_encoding(filepath)
        
        with open(filepath, 'r', encoding=encoding) as f:
            chunk_buffer = []
            current_size = 0
            chunk_idx = 0
            line_start = 0
            
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                
                if not line:  # Skip empty lines
                    continue
                
                line_size = len(line)
                
                # If adding this line exceeds chunk size, yield current chunk
                if current_size + line_size > self.chunk_size and chunk_buffer:
                    chunk_idx += 1
                    yield {
                        "text": "\n".join(chunk_buffer),
                        "metadata": {
                            "source": filepath,
                            "format": "txt",
                            "chunk_index": chunk_idx,
                            "lines": f"{line_start}-{line_num-1}",
                            "char_count": current_size
                        }
                    }
                    chunk_buffer = []
                    current_size = 0
                    line_start = line_num
                
                chunk_buffer.append(line)
                current_size += line_size
            
            # Yield remaining content
            if chunk_buffer:
                chunk_idx += 1
                yield {
                    "text": "\n".join(chunk_buffer),
                    "metadata": {
                        "source": filepath,
                        "format": "txt",
                        "chunk_index": chunk_idx,
                        "lines": f"{line_start}-{line_num}",
                        "char_count": current_size
                    }
                }


def test_ingestor():
    """Test function for development"""
    import tempfile
    
    # Test JSON
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump([{"company": "TestCo", "revenue": 1000000}], f)
        json_file = f.name
    
    # Test CSV
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False, encoding='utf-8') as f:
        f.write("company,revenue\n")
        f.write("TestCo,1000000\n")
        csv_file = f.name
    
    # Test TXT
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8') as f:
        f.write("Company analysis report.\nRevenue increased by 10%.")
        txt_file = f.name
    
    ingestor = PrivacyIngestor()
    
    print("\n=== Testing JSON ===")
    for chunk in ingestor.ingest_file(json_file):
        print(f"Chunk: {chunk['metadata']}")
        print(f"Text preview: {chunk['text'][:100]}...")
    
    print("\n=== Testing CSV ===")
    for chunk in ingestor.ingest_file(csv_file):
        print(f"Chunk: {chunk['metadata']}")
        print(f"Text preview: {chunk['text'][:100]}...")
    
    print("\n=== Testing TXT ===")
    for chunk in ingestor.ingest_file(txt_file):
        print(f"Chunk: {chunk['metadata']}")
        print(f"Text preview: {chunk['text'][:100]}...")
    
    # Cleanup
    import os
    os.unlink(json_file)
    os.unlink(csv_file)
    os.unlink(txt_file)
    
    print("\n✅ All tests passed!")


if __name__ == "__main__":
    test_ingestor()
