# pdf_extractor.py
import PyPDF2
import pdfplumber
import re
from typing import Dict, Any, List, Optional
import logging
from io import BytesIO

logger = logging.getLogger(__name__)


class PDFExtractor:
    """Extract data from PDF files including text, forms, and tables"""
    
    def __init__(self):
        self.text_patterns = self._compile_patterns()
    
    def _compile_patterns(self) -> Dict[str, re.Pattern]:
        """Compile regex patterns for common tax form fields"""
        return {
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'date': re.compile(r'\b\d{2}/\d{2}/\d{4}\b|\b\d{4}-\d{2}-\d{2}\b'),
            'amount': re.compile(r'\$?[\d,]+\.?\d{0,2}'),
            'zip_code': re.compile(r'\b\d{5}(?:-\d{4})?\b'),
            'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        }
    
    async def extract_pdf_data(self, pdf_content: bytes) -> Dict[str, Any]:
        """
        Extract all data from PDF including text, forms, and tables
        
        Args:
            pdf_content: PDF file content as bytes
            
        Returns:
            Dictionary containing extracted data
        """
        try:
            extracted_data = {
                'text_data': {},
                'form_fields': {},
                'tables': [],
                'metadata': {}
            }
            
            # Extract form fields using PyPDF2
            extracted_data['form_fields'] = await self._extract_form_fields(pdf_content)
            
            # Extract text and tables using pdfplumber
            text_data, tables = await self._extract_text_and_tables(pdf_content)
            extracted_data['text_data'] = text_data
            extracted_data['tables'] = tables
            
            # Extract metadata
            extracted_data['metadata'] = await self._extract_metadata(pdf_content)
            
            logger.info(f"Extracted {len(extracted_data['form_fields'])} form fields, "
                       f"{len(extracted_data['tables'])} tables")
            
            return extracted_data
            
        except Exception as e:
            logger.error(f"Error extracting PDF data: {str(e)}", exc_info=True)
            raise
    
    async def _extract_form_fields(self, pdf_content: bytes) -> Dict[str, Any]:
        """Extract form fields from PDF"""
        try:
            pdf_file = BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            form_fields = {}
            
            # Check if PDF has form fields
            if pdf_reader.get_fields():
                for field_name, field_data in pdf_reader.get_fields().items():
                    value = field_data.get('/V', '')
                    field_type = field_data.get('/FT', '')
                    
                    # Handle different field types
                    if field_type == '/Btn':  # Checkbox/Radio button
                        form_fields[field_name] = self._parse_checkbox_value(value)
                    else:
                        form_fields[field_name] = str(value) if value else None
            
            return form_fields
            
        except Exception as e:
            logger.warning(f"Error extracting form fields: {str(e)}")
            return {}
    
    async def _extract_text_and_tables(self, pdf_content: bytes) -> tuple:
        """Extract text and tables from PDF using pdfplumber"""
        try:
            pdf_file = BytesIO(pdf_content)
            text_data = {}
            all_tables = []
            
            with pdfplumber.open(pdf_file) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    page_text = page.extract_text()
                    if page_text:
                        text_data[f'page_{page_num}'] = page_text
                        
                        # Parse structured data from text
                        parsed_data = self._parse_text_data(page_text)
                        text_data.update(parsed_data)
                    
                    # Extract tables
                    tables = page.extract_tables()
                    if tables:
                        for table_idx, table in enumerate(tables):
                            all_tables.append({
                                'page': page_num,
                                'table_index': table_idx,
                                'data': table,
                                'parsed': self._parse_table(table)
                            })
            
            return text_data, all_tables
            
        except Exception as e:
            logger.warning(f"Error extracting text and tables: {str(e)}")
            return {}, []
    
    def _parse_text_data(self, text: str) -> Dict[str, Any]:
        """Parse structured data from text using patterns"""
        parsed = {}
        
        # Extract SSN
        ssn_matches = self.text_patterns['ssn'].findall(text)
        if ssn_matches:
            parsed['social_security_numbers'] = ssn_matches
        
        # Extract dates
        date_matches = self.text_patterns['date'].findall(text)
        if date_matches:
            parsed['dates'] = date_matches
        
        # Extract ZIP codes
        zip_matches = self.text_patterns['zip_code'].findall(text)
        if zip_matches:
            parsed['zip_codes'] = zip_matches
        
        # Extract key-value pairs (e.g., "Name: John Doe")
        kv_pattern = re.compile(r'([A-Za-z\s]+):\s*([^\n]+)')
        kv_matches = kv_pattern.findall(text)
        for key, value in kv_matches:
            clean_key = key.strip().lower().replace(' ', '_')
            parsed[clean_key] = value.strip()
        
        return parsed
    
    def _parse_table(self, table: List[List[str]]) -> Dict[str, Any]:
        """Parse table data into structured format"""
        if not table or len(table) < 2:
            return {}
        
        parsed = {
            'headers': table[0] if table else [],
            'rows': []
        }
        
        # Convert rows to dictionaries
        headers = table[0]
        for row in table[1:]:
            if len(row) == len(headers):
                row_dict = {
                    str(headers[i]).strip(): str(row[i]).strip() 
                    for i in range(len(headers))
                    if headers[i] and row[i]
                }
                if row_dict:
                    parsed['rows'].append(row_dict)
        
        return parsed
    
    async def _extract_metadata(self, pdf_content: bytes) -> Dict[str, Any]:
        """Extract PDF metadata"""
        try:
            pdf_file = BytesIO(pdf_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            metadata = {
                'num_pages': len(pdf_reader.pages),
                'info': {}
            }
            
            if pdf_reader.metadata:
                metadata['info'] = {
                    key: str(value) 
                    for key, value in pdf_reader.metadata.items()
                }
            
            return metadata
            
        except Exception as e:
            logger.warning(f"Error extracting metadata: {str(e)}")
            return {}
    
    def _parse_checkbox_value(self, value: Any) -> Optional[bool]:
        """Parse checkbox/radio button value"""
        if isinstance(value, str):
            value = value.lower()
            if value in ['yes', 'on', 'true', '1', 'checked']:
                return True
            elif value in ['no', 'off', 'false', '0', 'unchecked', '']:
                return False
        return None
