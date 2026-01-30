import sys
import analyseDescriptions
import model
import visualiseData

if __name__ == "__main__":
    analyzer = analyseDescriptions.JobDescriptionAnalyzer()
    if len(sys.argv) > 1:
        fileName = sys.argv[1]
        print(f"--- Using custom file: {fileName} ---")
    else:
        fileName = 'data/raw/testData.jsonl'
        print(f"--- No file provided. Using default: {fileName} ---")
    
    outputFile = 'data/processed/testOutput.csv'
    analyzer.run_analysis_from_file(fileName, outputFile)
    print(f"Analysis complete. Data saved to {outputFile}.")
    visualiseData.generate_polished_reports(outputFile)

