import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
from config import DATABASE_FILE
import seaborn as sns

def getNameValuePairs():
    df = pd.read_csv(DATABASE_FILE)

    for field in ['languages', 'frameworks', 'tools', 'cloud_platforms', 'domain_knowledge']:
        allEntries = []
        for entry in df[field].dropna():
            allEntries.extend([s.strip().lower() for s in str(entry).split(';')])
    
        # Plot the top 10
        counts = Counter(allEntries).most_common(10)
        names, values = zip(*counts)
        return names, values
        
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
        
def generate_polished_reports(df):
    # Set a professional theme
    sns.set_theme(style="whitegrid")
    df = pd.read_csv(df)
    for field in ['languages', 'frameworks', 'tools', 'cloud_platforms', 'domain_knowledge']:
        allEntries = []
        for entry in df[field].dropna():
            allEntries.extend([s.strip().lower() for s in str(entry).split(';')])
    
        # Plot the top 10
        counts = Counter(allEntries).most_common(10)
        names, values = zip(*counts)
        
        plt.figure(figsize=(10, 6))
        ax = sns.barplot(x=values, y=names, palette="viridis")
        
        plt.title(f"Top 10 {field.capitalize()}", fontsize=15)
        plt.xlabel("Frequency", fontsize=12)
        plt.ylabel("")
        sns.despine(left=True, bottom=True)
        plt.show()

if __name__ == "__main__":
    generate_polished_reports(DATABASE_FILE)