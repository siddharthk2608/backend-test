# chunk_manager.py (Enhanced Version)
import logging
from typing import Dict, Any, List, Tuple
import math

logger = logging.getLogger(__name__)


class ChunkManager:
    """Manage dynamic chunking of PDF pages based on PDF size"""
    
    def __init__(self, min_chunk_size: int = 3, max_chunk_size: int = 10):
        """
        Initialize ChunkManager
        
        Args:
            min_chunk_size: Minimum pages per chunk (default: 3)
            max_chunk_size: Maximum pages per chunk (default: 10)
        """
        self.min_chunk_size = max(3, min_chunk_size)  # Ensure minimum is at least 3
        self.max_chunk_size = max_chunk_size
        self.target_chunks = 5  # Ideal number of chunks for medium PDFs
    
    def calculate_chunk_size(self, total_pages: int) -> int:
        """
        Calculate optimal chunk size based on total pages
        GUARANTEED MINIMUM: 3 pages per chunk
        
        Strategy:
        - Tiny PDFs (1-9 pages): 3 pages/chunk
        - Small PDFs (10-20 pages): 3-4 pages/chunk
        - Medium PDFs (21-50 pages): 5-7 pages/chunk
        - Large PDFs (51-100 pages): 7-10 pages/chunk
        - Huge PDFs (100+ pages): 10 pages/chunk (max)
        
        Args:
            total_pages: Total number of pages in PDF
            
        Returns:
            Optimal chunk size (guaranteed >= 3)
        """
        if total_pages <= 0:
            return self.min_chunk_size
        
        # Tiny PDFs: Use minimum chunk size
        if total_pages < 10:
            chunk_size = self.min_chunk_size
            logger.info(f"📘 Tiny PDF ({total_pages} pages): Using {chunk_size} pages/chunk")
            return chunk_size
        
        # Small PDFs (10-20 pages): 3-4 pages per chunk
        elif total_pages <= 20:
            # For 10 pages: 3 pages/chunk (4 chunks)
            # For 20 pages: 4 pages/chunk (5 chunks)
            chunk_size = max(self.min_chunk_size, min(4, math.ceil(total_pages / 5)))
            logger.info(f"📗 Small PDF ({total_pages} pages): Using {chunk_size} pages/chunk")
            return chunk_size
        
        # Medium PDFs (21-50 pages): 5-7 pages per chunk
        elif total_pages <= 50:
            # Aim for 5-8 chunks
            chunk_size = max(self.min_chunk_size, math.ceil(total_pages / 7))
            chunk_size = min(chunk_size, 7)
            logger.info(f"📙 Medium PDF ({total_pages} pages): Using {chunk_size} pages/chunk")
            return chunk_size
        
        # Large PDFs (51-100 pages): 7-10 pages per chunk
        elif total_pages <= 100:
            # Aim for 8-12 chunks
            chunk_size = max(self.min_chunk_size, math.ceil(total_pages / 10))
            chunk_size = min(chunk_size, self.max_chunk_size)
            logger.info(f"Large PDF ({total_pages} pages): Using {chunk_size} pages/chunk")
            return chunk_size
        
        # Huge PDFs (100+ pages): Use maximum chunk size
        else:
            chunk_size = self.max_chunk_size
            num_chunks = math.ceil(total_pages / chunk_size)
            logger.info(f"📚 Huge PDF ({total_pages} pages): Using {chunk_size} pages/chunk "
                       f"(~{num_chunks} chunks)")
            return chunk_size
    
    def create_chunks(self, pages_data: Dict[int, Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Create chunks from pages data with guaranteed minimum size
        
        Args:
            pages_data: Dictionary of page data keyed by page number
            
        Returns:
            List of chunks, each containing at least 3 pages (when possible)
        """
        if not pages_data:
            return []
        
        total_pages = len(pages_data)
        chunk_size = self.calculate_chunk_size(total_pages)
        
        # Ensure we never create chunks smaller than minimum
        if chunk_size < self.min_chunk_size:
            chunk_size = self.min_chunk_size
        
        chunks = []
        page_numbers = sorted(pages_data.keys())
        
        i = 0
        while i < len(page_numbers):
            # Calculate how many pages for this chunk
            remaining_pages = len(page_numbers) - i
            
            # If this is the last chunk and it would be too small, merge with previous
            if remaining_pages < self.min_chunk_size and len(chunks) > 0:
                # Add remaining pages to the last chunk
                last_chunk = chunks[-1]
                for page_num in page_numbers[i:]:
                    last_chunk['pages'][page_num] = pages_data[page_num]
                last_chunk['end_page'] = page_numbers[-1]
                last_chunk['page_count'] = len(last_chunk['pages'])
                logger.debug(f"Merged {remaining_pages} remaining pages into last chunk")
                break
            
            # Create normal chunk
            end_idx = min(i + chunk_size, len(page_numbers))
            chunk_page_nums = page_numbers[i:end_idx]
            
            chunk = {
                'chunk_id': len(chunks) + 1,
                'start_page': chunk_page_nums[0],
                'end_page': chunk_page_nums[-1],
                'page_count': len(chunk_page_nums),
                'pages': {}
            }
            
            # Add pages to this chunk
            for page_num in chunk_page_nums:
                chunk['pages'][page_num] = pages_data[page_num]
            
            chunks.append(chunk)
            i = end_idx
        
        # Verify all chunks meet minimum size (except possibly the last one for tiny PDFs)
        for chunk in chunks[:-1]:  # Check all but last chunk
            assert chunk['page_count'] >= self.min_chunk_size, \
                f"Chunk {chunk['chunk_id']} has only {chunk['page_count']} pages (minimum: {self.min_chunk_size})"
        
        logger.info(f" Created {len(chunks)} chunks from {total_pages} pages "
                   f"(~{chunk_size} pages/chunk, min {self.min_chunk_size} guaranteed)")
        
        # Log chunk details
        for chunk in chunks:
            logger.debug(f"   Chunk {chunk['chunk_id']}: "
                        f"pages {chunk['start_page']}-{chunk['end_page']} "
                        f"({chunk['page_count']} pages)")
        
        return chunks
    
    def get_chunk_summary(self, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get detailed summary information about chunks"""
        if not chunks:
            return {
                'total_chunks': 0,
                'total_pages': 0,
                'avg_pages_per_chunk': 0,
                'min_pages_in_chunk': 0,
                'max_pages_in_chunk': 0,
                'chunk_details': []
            }
        
        total_pages = sum(chunk['page_count'] for chunk in chunks)
        avg_pages = total_pages / len(chunks)
        min_pages = min(chunk['page_count'] for chunk in chunks)
        max_pages = max(chunk['page_count'] for chunk in chunks)
        
        chunk_details = [
            {
                'chunk_id': chunk['chunk_id'],
                'page_range': f"{chunk['start_page']}-{chunk['end_page']}",
                'page_count': chunk['page_count']
            }
            for chunk in chunks
        ]
        
        return {
            'total_chunks': len(chunks),
            'total_pages': total_pages,
            'avg_pages_per_chunk': round(avg_pages, 1),
            'min_pages_in_chunk': min_pages,
            'max_pages_in_chunk': max_pages,
            'min_chunk_size_guaranteed': self.min_chunk_size,
            'chunk_details': chunk_details
        }
    
    def estimate_api_calls(self, total_pages: int) -> Dict[str, Any]:
        """
        Estimate the number of API calls needed for a PDF
        
        Args:
            total_pages: Total number of pages
            
        Returns:
            Dictionary with estimates
        """
        chunk_size = self.calculate_chunk_size(total_pages)
        estimated_chunks = math.ceil(total_pages / chunk_size)
        
        # Estimate early stopping (assuming 50% chance of early stop)
        estimated_with_early_stop = max(1, math.ceil(estimated_chunks * 0.6))
        potential_savings = estimated_chunks - estimated_with_early_stop
        
        return {
            'total_pages': total_pages,
            'chunk_size': chunk_size,
            'max_api_calls': estimated_chunks,
            'estimated_api_calls_with_early_stop': estimated_with_early_stop,
            'potential_api_call_savings': potential_savings,
            'estimated_cost_per_call_usd': 0.01,  # Example cost
            'max_cost_usd': round(estimated_chunks * 0.01, 2),
            'estimated_cost_with_early_stop_usd': round(estimated_with_early_stop * 0.01, 2)
        }