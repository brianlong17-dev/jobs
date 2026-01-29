import csv
import os
import re
import time
import instructor
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv
from google.genai import types
from model import JobAnalysisSimple, JobAnalysisComplex
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

class JobDescriptionAnalyzer:
    def __init__(self, api_model_name: str = "google/gemini-2.5-flash-lite", analysisModel: BaseModel = JobAnalysisComplex):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        self.api_model_name = api_model_name
        self.client = instructor.from_provider(
            self.api_model_name,
            api_key=api_key)
        self.analysisModel = analysisModel
        self.output_file = 'data/processed/market_data' + time.strftime("%Y%m%d_%H%M%S") + '.csv'
        
    def run_analysis_from_file(self, file_path: str, delimiter: str = r'(?i)Full job description', limit: Optional[int] = None) -> str:
        job_descriptions = self.extract_text_from_file(file_path, delimiter)
        if limit is not None:
            job_descriptions = job_descriptions[:limit]
            print(f"--- Limit: {limit} jobs. Starting Analysis... ---")
        else:
            print(f"--- Found {len(job_descriptions)} jobs. Starting Analysis... ---")
        for i, job_text in enumerate(job_descriptions):
            self.process_job_description(job_text)
        
        return self.output_file
    
    def extract_text_from_file(self, file_path: str, delimiter: str) -> list[str]:
        """
        Reads a file and splits it into a list of job descriptions.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file '{file_path}' was not found.")

        with open(file_path, 'r', encoding='utf-8') as f:
            blob = f.read()
            
        jobs = re.split(delimiter, blob)
        
        # Clean up and filter short/empty strings
        return [j.strip() for j in jobs if len(j.strip()) > 100]
    
    @retry(
        stop=stop_after_attempt(3), 
        wait=wait_exponential(multiplier=1, min=4, max=10),
        before_sleep=lambda retry_state: print(f"⚠️ Retrying AI call (Attempt {retry_state.attempt_number})...")
    )
    def process_job_description(self, job_text: str):
        jsonData = self.client.create(
            response_model=self.analysisModel,
            messages=[{"role": "user", "content": f"Extract tech details from this job post:\n\n{job_text}"}],
        )
        self._save_to_csv(jsonData)
        self._display_analysis(jsonData)
            
    def _display_analysis(self, jsonData):
        # Moves the printing logic out of the main logic path
        BOLD, BLUE, RESET = "\033[1m", "\033[94m", "\033[0m"
        for field, value in jsonData.model_dump().items():
            display_name = field.replace("_", " ").title()
            print(f"{BOLD}{BLUE}{display_name: <20}{RESET}: {value}")
        print("-" * 40)
        
    def _save_to_csv(self, jsonData):
        
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        file_exists = os.path.isfile(self.output_file)
        
        fieldnames = list(self.analysisModel.model_fields.keys())

        with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
            # QUOTE_MINIMAL (default) adds quotes if the data contains a comma.
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL)
            if not file_exists:
                writer.writeheader()

            row = jsonData.model_dump()
            
            # 2. Process lists: Join with a semi-colon or comma
            # Pro-tip: Using a semi-colon (;) inside the quotes 
            # makes it even easier to split later without confusion.
            
            # formatted_row = {}
            # for field in fieldnames:
            #     val = row.get(field, "")
            #     if isinstance(val, list):
            #         formatted_row[field] = "; ".join(map(str, val))
            #     else:
            #         formatted_row[field] = val

            # writer.writerow(formatted_row)
            
            for field in fieldnames:
                if field in row and isinstance(row[field], list):
                    row[field] = "; ".join(row[field]) if row[field] else ""

            writer.writerow(row)
    
if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG)
    analyzer = JobDescriptionAnalyzer()
    fileName = 'data/raw/testData.txt'
    outputFile = analyzer.run_analysis_from_file(fileName)
    print(f"Analysis complete. Data saved to {outputFile}.")
    

