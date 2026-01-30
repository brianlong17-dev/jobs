import csv
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import time
import instructor
from pydantic import BaseModel, Field
from typing import List, Optional
from dotenv import load_dotenv
from google.genai import types
from model import JobAnalysisSimple, JobAnalysisComplex
from tenacity import retry, stop_after_attempt, wait_exponential
from config import QUEUE_FILE, DATABASE_FILE
import logging

class JobDescriptionAnalyzer:
    def __init__(self, api_model_name: str = "google/gemini-2.5-flash-lite", 
                 analysisModel: BaseModel = JobAnalysisComplex, limit = None):
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set.")
        self.api_model_name = api_model_name
        self.client = instructor.from_provider(
            self.api_model_name,
            api_key=api_key)
        self.analysis_model = analysisModel
        self.output_file = DATABASE_FILE
        self.input_file = QUEUE_FILE
        self.limit = limit
        self.processed_count = 0
        self.processed_ids = set()
        self.initProcessedIDs()
        
    def initProcessedIDs(self):
        with open(self.output_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            # Skip the header row
            next(reader, None) 
            for row in reader:
                if row:  # Ensure the row isn't empty
                    # Assuming ID is the first element (index 0)
                    self.processed_ids.add(row[0])
        print("Current processed IDS: ", self.processed_ids)
        
        
    def run_analysis_from_file(self, input_file: str = None, output_file: str = None) -> str:
        if output_file != None:
            self.output_file = output_file
        if input_file != None:
            self.input_file = input_file
        job_descriptions = self.extract_text_from_file(self.input_file)
        if self.limit is not None:
            print(f"--- Limit: {self.limit} jobs. Starting Analysis... ---")
        else:
            print(f"--- Found {len(job_descriptions)} jobs. Starting Analysis... ---")
            
        for i, job_json in enumerate(job_descriptions):
            if job_json['id'] not in self.processed_ids:
                if self.limit is not None and self.processed_count >= self.limit:
                    print(f"--- Limit of {self.limit} reached. Stopping. ---")
                    break
                self.process_job_description(job_json)
                self.processed_count += 1
            else:
                print(f"--- Skipping job with ID: {job_json['id']} ---")
            
        if self.limit == None:
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
            name_only = Path(self.input_file).stem
            archive_path = f"data/archive/processed_{name_only}_{timestamp}.jsonl"

            os.makedirs("data/archive", exist_ok=True)
            shutil.move(self.input_file, archive_path)
        return self.output_file
    
    def extract_text_from_file(self, file_path: str) -> list[str]:
        """
        Reads a file and splits it into a list of job descriptions.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"The file '{file_path}' was not found.")
        jobs = []

        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
            # Skip empty lines to be safe
                if line.strip(): 
                    job = json.loads(line)
                    jobs.append(job)
        return jobs

    
    # @retry(
    #     stop=stop_after_attempt(3), 
    #     wait=wait_exponential(multiplier=1, min=4, max=10),
    #     before_sleep=lambda retry_state: print(f"⚠️ Retrying AI call (Attempt {retry_state.attempt_number})...")
    # )
    def process_job_description(self, job_json ):
        job_text_for_ai = f"JOB TITLE: {job_json.get('title')}\n\n{job_json.get('description')}"
        
        jsonData = self.client.create(
            response_model=self.analysis_model,
            messages=[{"role": "user", "content": f"Extract tech details from this job post:\n\n{job_text_for_ai}"}],
        )
        analysis_dict = jsonData.model_dump()
        final_record = {**job_json, **analysis_dict}
        if 'description' in final_record:
            del final_record['description']
        
        self._save_to_csv(final_record)
        self._display_analysis(final_record)
        #remove line from file?
            
    def _display_analysis(self, jsonData):
        # Moves the printing logic out of the main logic path
        BOLD, BLUE, RESET = "\033[1m", "\033[94m", "\033[0m"
        for field, value in jsonData.items():
            display_name = field.replace("_", " ").title()
            print(f"{BOLD}{BLUE}{display_name: <20}{RESET}: {value}")
        print("-" * 40)
        
    def _save_to_csv(self, jsonData):
        
        os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
        file_exists = os.path.isfile(self.output_file)
        
        fieldnames = ['id', 'title', 'company', 'location'] + list(self.analysis_model.model_fields.keys())

        with open(self.output_file, 'a', newline='', encoding='utf-8') as f:
            # QUOTE_MINIMAL (default) adds quotes if the data contains a comma.
            writer = csv.DictWriter(f, fieldnames=fieldnames, quoting=csv.QUOTE_MINIMAL, extrasaction='ignore')
            if not file_exists:
                writer.writeheader()

            row = jsonData.copy()
            
            for field in fieldnames:
                if field in row and isinstance(row[field], list):
                    row[field] = "; ".join(row[field]) if row[field] else ""

            writer.writerow(row)
    
if __name__ == "__main__":
    #logging.basicConfig(level=logging.DEBUG)
    analyzer = JobDescriptionAnalyzer(limit=None)
    outputFile = analyzer.run_analysis_from_file()
    print(f"Analysis complete. Data saved to {outputFile}.")
    

