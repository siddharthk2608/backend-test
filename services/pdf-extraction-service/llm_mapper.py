# llm_mapper.py
import google.generativeai as genai
import json
import logging
from typing import Dict, Any, Optional, List
import os
from models import TaxReturnAnswers
import asyncio
from chunk_manager import ChunkManager

logger = logging.getLogger(__name__)


class LLMMapper:
    """Map extracted PDF data to structured format using Gemini LLM with dynamic chunking and early stopping"""
    
    def __init__(self):
        # Configure Gemini API
        genai.configure(api_key='AIzaSyBrCDaECvgQLeju542GD7SBOnPzG3abU6k')
        
        # Initialize the model
        self.model = genai.GenerativeModel(
            model_name='gemini-2.5-flash',
            generation_config={
                'temperature': 0,
                'top_p': 0.95,
                'top_k': 40,
                'max_output_tokens': 8192,
            }
        )
        
        self.field_schema = self._get_field_schema()
        self.chunk_manager = ChunkManager()
        
        # Track required fields (excluding client_notes as it's optional)
        self.required_fields = [
            field for field in self.field_schema.keys() 
            if field != 'client_notes'
        ]
    
    def _get_field_schema(self) -> Dict[str, Any]:
        """Get the schema for output fields with detailed descriptions"""
        return {
            "your_first_name": {
                "type": "string", 
                "description": "First name of the taxpayer",
                "priority": "high"
            },
            "your_last_name": {
                "type": "string", 
                "description": "Last name of the taxpayer",
                "priority": "high"
            },
            "your_date_of_birth": {
                "type": "string", 
                "format": "YYYY-MM-DD", 
                "description": "Date of birth",
                "priority": "high"
            },
            "your_social_security_number": {
                "type": "string", 
                "description": "Social security number (format: XXX-XX-XXXX)",
                "priority": "high"
            },
            "your_occupation": {
                "type": "string", 
                "description": "Current occupation or job title",
                "priority": "medium"
            },
            "are_you_married_": {
                "type": "boolean", 
                "description": "Marital status (true if married/filing jointly, false if single)",
                "priority": "high"
            },
            "wages_current_year_not_owned": {
                "type": "string", 
                "description": "Current year wages from W-2 or income statements (as string number)",
                "priority": "high"
            },
            "wages_next_year_not_owned": {
                "type": "string", 
                "description": "Projected or estimated next year wages",
                "priority": "low"
            },
            "do_you_have_any_children_": {
                "type": "boolean", 
                "description": "Whether taxpayer has children/dependents",
                "priority": "medium"
            },
            "your_street_address": {
                "type": "string", 
                "description": "Street address (number and street name)",
                "priority": "high"
            },
            "your_city": {
                "type": "string", 
                "description": "City name",
                "priority": "high"
            },
            "your_zip_code": {
                "type": "string", 
                "description": "ZIP code (5 digits or ZIP+4 format)",
                "priority": "high"
            },
            "plan_work_at_home": {
                "type": "boolean", 
                "description": "Plans to work from home or has home office",
                "priority": "medium"
            },
            "home_square_footage": {
                "type": "string", 
                "description": "Total home square footage",
                "priority": "medium"
            },
            "home_office_square_footage": {
                "type": "string", 
                "description": "Home office square footage used for business",
                "priority": "medium"
            },
            
            # WOTC (Work Opportunity Tax Credit) fields
            "wotc_group1": {
                "type": "string", 
                "description": "Total number of employees: Qualified Veteran (less than 1 year post-discharge)",
                "priority": "low"
            },
            "wotc_group2": {
                "type": "string", 
                "description": "Total number of employees: Qualified Veteran (unemployed 4-6 months)",
                "priority": "low"
            },
            "wotc_group3": {
                "type": "string", 
                "description": "Total number of employees: Qualified Veteran (unemployed 6+ months)",
                "priority": "low"
            },
            "wotc_group4": {
                "type": "string", 
                "description": "Total number of employees: Qualified Veteran with disability (unemployed 6+ months)",
                "priority": "low"
            },
            "wotc_group5": {
                "type": "string", 
                "description": "Total number of employees: Qualified Summer Youth Employee",
                "priority": "low"
            },
            "wotc_group6": {
                "type": "string", 
                "description": "Total number of employees: Long-Term Family Assistance recipients",
                "priority": "low"
            },
            
            "export_net_profit": {
                "type": "string", 
                "description": "Net profit from export sales or international business",
                "priority": "low"
            },
            "export_gross_revenue": {
                "type": "string", 
                "description": "Gross revenue from export sales",
                "priority": "low"
            },
            "other_income_notes": {
                "type": "string", 
                "description": "Additional notes about other income sources",
                "priority": "low"
            },
            "home_office_expenses_notes": {
                "type": "string", 
                "description": "Notes about home office expenses",
                "priority": "low"
            },
            "international_notes": {
                "type": "string", 
                "description": "Notes about international transactions",
                "priority": "low"
            },
            "client_notes": {
                "type": "string", 
                "description": "Any additional client notes or comments",
                "priority": "optional"
            }
        }
    
    def _check_completion(self, current_data: Dict[str, Any]) -> tuple[bool, int, int]:
        """Check if all required fields are filled"""
        filled_count = 0
        total_count = len(self.required_fields)
        
        for field in self.required_fields:
            value = current_data.get(field)
            if value is not None and value != "":
                filled_count += 1
        
        is_complete = filled_count == total_count
        return is_complete, filled_count, total_count
    
    def _get_missing_fields(self, current_data: Dict[str, Any]) -> List[str]:
        """Get list of fields that are still missing"""
        missing_fields = []
        for field in self.required_fields:
            value = current_data.get(field)
            if value is None or value == "":
                missing_fields.append(field)
        return missing_fields
    
    async def map_to_structure(self, extracted_data: Dict[str, Any]) -> TaxReturnAnswers:
        """
        Map extracted PDF data to structured format using Gemini LLM
        Process in dynamic chunks with early stopping when all fields are filled
        
        Args:
            extracted_data: Raw data extracted from PDF organized by pages
            
        Returns:
            TaxReturnAnswers object with mapped data
        """
        try:
            # Organize data by pages
            pages_data = self._organize_data_by_pages(extracted_data)
            total_pages = len(pages_data)
            
            # Create dynamic chunks
            chunks = self.chunk_manager.create_chunks(pages_data)
            chunk_summary = self.chunk_manager.get_chunk_summary(chunks)
            
            logger.info(f"Dynamic chunking created {chunk_summary['total_chunks']} chunks "
                       f"from {total_pages} pages "
                       f"(avg {chunk_summary['avg_pages_per_chunk']} pages/chunk)")
            
            # Initialize merged data
            merged_data = {field: None for field in self.field_schema.keys()}
            
            # Process each chunk
            chunks_processed = 0
            api_calls_saved = 0
            
            for chunk in chunks:
                chunks_processed += 1
                
                # Check current completion status
                is_complete, filled_count, total_count = self._check_completion(merged_data)
                
                if is_complete:
                    remaining_chunks = len(chunks) - chunks_processed + 1
                    api_calls_saved = remaining_chunks
                    logger.info(f" All {total_count} required fields filled!")
                    logger.info(f" Early stopping at chunk {chunks_processed}/{len(chunks)} "
                               f"(pages {chunk['start_page']}-{chunk['end_page']})")
                    logger.info(f" Saved {api_calls_saved} API calls by stopping early")
                    break
                
                # Log progress
                missing_fields = self._get_missing_fields(merged_data)
                logger.info(f" Processing chunk {chunks_processed}/{len(chunks)} "
                           f"(pages {chunk['start_page']}-{chunk['end_page']}, "
                           f"{chunk['page_count']} pages)")
                logger.info(f"   Progress: {filled_count}/{total_count} fields filled, "
                           f"{len(missing_fields)} remaining")
                
                # Process this chunk
                chunk_result = await self._process_chunk(chunk, missing_fields)
                
                # Merge results immediately
                merged_data = self._merge_chunk_result(merged_data, chunk_result, chunk)
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.5)
            
            # Final completion check
            is_complete, filled_count, total_count = self._check_completion(merged_data)
            
            if is_complete:
                logger.info(f"Successfully filled all {total_count} required fields")
            else:
                logger.warning(f" Processed all {len(chunks)} chunks but only filled "
                             f"{filled_count}/{total_count} fields")
                missing = self._get_missing_fields(merged_data)
                logger.warning(f"Missing fields: {', '.join(missing)}")
            
            # Validate and fill missing fields with defaults
            validated_data = self._validate_and_fill(merged_data)
            
            # Log final stats
            logger.info(f"🏁 Processing complete: {chunks_processed}/{len(chunks)} chunks processed, "
                       f"{filled_count}/{total_count} fields filled, "
                       f"{api_calls_saved} API calls saved")
            
            # Create TaxReturnAnswers object
            return TaxReturnAnswers(**validated_data)
            
        except Exception as e:
            logger.error(f"Error mapping data with LLM: {str(e)}", exc_info=True)
            return TaxReturnAnswers()
    
    def _organize_data_by_pages(self, extracted_data: Dict[str, Any]) -> Dict[int, Dict[str, Any]]:
        """Organize extracted data by page numbers"""
        pages_data = {}
        
        # Get page text data
        text_data = extracted_data.get('text_data', {})
        for key, value in text_data.items():
            if key.startswith('page_'):
                try:
                    page_num = int(key.split('_')[1])
                    if page_num not in pages_data:
                        pages_data[page_num] = {
                            'text': '',
                            'form_fields': {},
                            'tables': [],
                            'parsed_data': {}
                        }
                    pages_data[page_num]['text'] = value
                except (IndexError, ValueError):
                    continue
            else:
                if 1 not in pages_data:
                    pages_data[1] = {
                        'text': '',
                        'form_fields': {},
                        'tables': [],
                        'parsed_data': {}
                    }
                pages_data[1]['parsed_data'][key] = value
        
        # Add form fields
        form_fields = extracted_data.get('form_fields', {})
        if form_fields:
            if 1 not in pages_data:
                pages_data[1] = {
                    'text': '',
                    'form_fields': {},
                    'tables': [],
                    'parsed_data': {}
                }
            pages_data[1]['form_fields'] = form_fields
        
        # Add tables by page
        tables = extracted_data.get('tables', [])
        for table in tables:
            page_num = table.get('page', 1)
            if page_num not in pages_data:
                pages_data[page_num] = {
                    'text': '',
                    'form_fields': {},
                    'tables': [],
                    'parsed_data': {}
                }
            pages_data[page_num]['tables'].append(table)
        
        return dict(sorted(pages_data.items()))
    
    async def _process_chunk(
        self, 
        chunk: Dict[str, Any],
        missing_fields: List[str]
    ) -> Dict[str, Any]:
        """
        Process a chunk of pages with LLM
        
        Args:
            chunk: Chunk containing multiple pages
            missing_fields: List of fields still needed
            
        Returns:
            Mapped data from this chunk
        """
        try:
            # Prepare chunk data for LLM
            input_data = self._prepare_chunk_data(chunk)
            
            # Create prompt for this chunk
            prompt = self._create_chunk_mapping_prompt(chunk, input_data, missing_fields)
            
            # Call Gemini API
            logger.debug(f"Calling Gemini API for chunk {chunk['chunk_id']}...")
            response = self.model.generate_content(prompt)
            
            # Parse response
            mapped_data = self._parse_llm_response(response.text)
            
            # Count how many missing fields were found
            found_count = sum(
                1 for field in missing_fields 
                if mapped_data.get(field) is not None and mapped_data.get(field) != ""
            )
            
            logger.info(f"    Found {found_count}/{len(missing_fields)} missing fields in this chunk")
            
            return mapped_data
            
        except Exception as e:
            logger.error(f"Error processing chunk {chunk['chunk_id']}: {str(e)}")
            return {}
    
    def _prepare_chunk_data(self, chunk: Dict[str, Any]) -> str:
        """Prepare chunk data for LLM input"""
        input_parts = [
            f"CHUNK {chunk['chunk_id']} - PAGES {chunk['start_page']}-{chunk['end_page']} "
            f"({chunk['page_count']} pages):"
        ]
        input_parts.append("=" * 70)
        
        # Process each page in the chunk
        for page_num, page_data in sorted(chunk['pages'].items()):
            input_parts.append(f"\n--- PAGE {page_num} ---")
            
            # Add form fields
            if page_data.get('form_fields'):
                input_parts.append("FORM FIELDS:")
                for key, value in list(page_data['form_fields'].items())[:20]:  # Limit
                    input_parts.append(f"  {key}: {value}")
            
            # Add parsed data
            if page_data.get('parsed_data'):
                input_parts.append("PARSED DATA:")
                for key, value in list(page_data['parsed_data'].items())[:10]:  # Limit
                    input_parts.append(f"  {key}: {value}")
            
            # Add page text (limited)
            if page_data.get('text'):
                text = page_data['text'][:2000]  # Limit per page
                input_parts.append(f"TEXT: {text}...")
            
            # Add tables
            if page_data.get('tables'):
                input_parts.append(f"TABLES ({len(page_data['tables'])}):")
                for idx, table in enumerate(page_data['tables'][:3]):  # Limit tables
                    if table.get('parsed', {}).get('rows'):
                        input_parts.append(f"  Table {idx + 1}:")
                        for row in table['parsed']['rows'][:5]:  # Limit rows
                            input_parts.append(f"    {row}")
        
        return "\n".join(input_parts)
    
    def _create_chunk_mapping_prompt(
        self, 
        chunk: Dict[str, Any],
        input_data: str,
        missing_fields: List[str]
    ) -> str:
        """Create the prompt for a chunk"""
        
        # Get schema for missing fields only
        missing_schema = {
            field: self.field_schema[field] 
            for field in missing_fields 
            if field in self.field_schema
        }
        
        schema_description = "\n".join([
            f"- {field}: {info['description']} (type: {info['type']}, priority: {info.get('priority', 'medium')})"
            for field, info in missing_schema.items()
        ])
        
        # Highlight high priority fields
        high_priority_fields = [
            field for field in missing_fields 
            if self.field_schema.get(field, {}).get('priority') == 'high'
        ]
        
        prompt = f"""You are a tax document processing expert. Extract data from this CHUNK of pages.

**CHUNK INFO:**
- Chunk {chunk['chunk_id']}
- Pages: {chunk['start_page']} to {chunk['end_page']}
- Total pages in chunk: {chunk['page_count']}

**FOCUS ON THESE {len(missing_fields)} MISSING FIELDS:**
{schema_description}

{'**HIGH PRIORITY (extract first):** ' + ', '.join(high_priority_fields) if high_priority_fields else ''}

**DATA FROM THIS CHUNK:**
{input_data}

**INSTRUCTIONS:**
1. Extract the missing fields listed above from ANY page in this chunk
2. Combine information from multiple pages if needed
3. For fields not in this chunk, use null
4. Dates: YYYY-MM-DD format
5. Booleans: true/false
6. Numbers as strings: "75000"
7. SSN format: XXX-XX-XXXX

**LOOK FOR:**
- Names: Top of forms, W-2s, signatures
- SSN: "Social Security number" boxes
- Address: Header sections, mailing addresses
- Marital status: Filing status checkboxes
- Wages: W-2 box 1, income summaries
- WOTC: Form 8850, Form 5884, employee counts

**OUTPUT JSON ONLY:**
{{
  "field_name": "value or null"
}}"""
        
        return prompt
    
    def _merge_chunk_result(
        self, 
        current_data: Dict[str, Any], 
        chunk_result: Dict[str, Any],
        chunk: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Merge a chunk result into current data"""
        for field, value in chunk_result.items():
            if field in current_data:
                # Only update if we don't have a value yet
                if current_data[field] is None and value is not None and value != "":
                    current_data[field] = value
                    logger.debug(f"       Found '{field}' in chunk {chunk['chunk_id']}")
                # Or if new value is more complete
                elif value is not None and value != "":
                    if isinstance(value, str) and isinstance(current_data[field], str):
                        if len(str(value)) > len(str(current_data[field])):
                            current_data[field] = value
                            logger.debug(f"      ↻ Updated '{field}' with better value")
        
        return current_data
    
    def _parse_llm_response(self, response_text: str) -> Dict[str, Any]:
        """Parse LLM response to extract JSON"""
        try:
            text = response_text.strip()
            
            # Remove markdown
            if text.startswith("```json"):
                text = text[7:]
            elif text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            text = text.strip()
            
            # Extract JSON
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_text = text[start_idx:end_idx + 1]
                parsed = json.loads(json_text)
                return parsed
            else:
                logger.error("No JSON object found in response")
                return {}
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing LLM response as JSON: {str(e)}")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error parsing response: {str(e)}")
            return {}
    
    def _validate_and_fill(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate mapped data and fill missing fields with defaults"""
        validated = {}
        
        for field, schema in self.field_schema.items():
            value = data.get(field)
            
            if value is None or value == "":
                if schema['type'] == 'boolean':
                    validated[field] = None
                elif schema['type'] == 'string':
                    validated[field] = None if field != 'client_notes' else ""
                else:
                    validated[field] = None
            else:
                if schema['type'] == 'boolean':
                    if isinstance(value, str):
                        validated[field] = value.lower() in ['true', 'yes', '1', 'checked', 'x']
                    else:
                        validated[field] = bool(value)
                elif schema['type'] == 'string':
                    validated[field] = str(value).strip()
                else:
                    validated[field] = value
        
        return validated