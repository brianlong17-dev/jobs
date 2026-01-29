import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter

def generate_reports(csv_path: str):
    df = pd.read_csv(csv_path)

    for field in ['languages', 'frameworks', 'tools', 'cloud_platforms', 'domain_knowledge']:
        allEntries = []
        for entry in df[field].dropna():
            allEntries.extend([s.strip().lower() for s in str(entry).split(';')])
    
        # Plot the top 10
        counts = Counter(allEntries).most_common(10)
        names, values = zip(*counts)

        plt.barh(names, values, color='skyblue')
        plt.title("Most Demanded " + field.capitalize() + " in My Scrape")
        plt.xlabel("Number of Job Posts")
        plt.show()
    

if __name__ == "__main__":
    generate_reports('output/market_data20260128_160008.csv')