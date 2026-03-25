# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pandas",
#   "matplotlib",
#   "seaborn",
#   "scikit-learn",
#   "openai"
# ]
# ///

import sys
import os
import json
import re
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

from openai import OpenAI

def clean_name(col):
    return re.sub(r'[^a-zA-Z0-9]', '_', col).lower()

# DEFINING THE LLM CLIENT(GROQ)
def get_llm():
   return OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1"
   )
# LOADING THE DATASET FILE
def load_dataset(file):

    try:
        df = pd.read_csv(file, encoding="utf-8")

    except UnicodeDecodeError:

        try:
            df = pd.read_csv(file, encoding="latin1")

        except UnicodeDecodeError:

            df = pd.read_csv(file, encoding="cp1252")

    return df
# PERFORMING BASIC ANALYSIS

def basic_analysis(df):

    numeric = df.select_dtypes(include=["number"])
    categorical = df.select_dtypes(include=["object","string"])

    summary = {
        "shape": df.shape,
        "columns": list(df.columns),
        "numeric_columns": list(numeric.columns),
        "categorical_columns": list(categorical.columns),
        "missing_values": df.isnull().sum().to_dict(),
        "summary_statistics": numeric.describe().to_string()
    }

    return summary

# CORRELATION ANALYSIS

def correlation_analysis(df):

    numeric = df.select_dtypes(include=["number"])

    if len(numeric.columns) < 2:
        return []

    corr = numeric.corr()

    strong_corr = []

    for i in corr.columns:
        for j in corr.columns:

            if i < j and abs(corr.loc[i,j]) > 0.6:

                strong_corr.append((i,j,round(corr.loc[i,j],2)))

    return strong_corr
# OUTLIER DETECTION

def detect_outliers(df):

    numeric = df.select_dtypes(include=["number"])

    outliers = {}

    for col in numeric.columns:

        Q1 = numeric[col].quantile(0.25)
        Q3 = numeric[col].quantile(0.75)

        IQR = Q3 - Q1

        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR

        count = ((numeric[col] < lower) | (numeric[col] > upper)).sum()

        outliers[col] = int(count)

    return outliers

# CLUSTER ANALYSIS
def cluster_analysis(df):

    important_cols = select_important_features(df)
    numeric = df[important_cols]

    if len(numeric.columns) < 2:
        return df

    scaler = StandardScaler()

    scaled = scaler.fit_transform(numeric.fillna(0))

    model = KMeans(n_clusters=3, random_state=42)

    clusters = model.fit_predict(scaled)

    df["cluster"] = clusters

    return df


# PCA CLUSTER VISUALIZATION
def pca_visualization(df, output_dir):

    numeric = df.select_dtypes(include=["number"])

    if "cluster" not in df.columns or len(numeric.columns) < 2:
        return

    scaler = StandardScaler()
    scaled = scaler.fit_transform(numeric.fillna(0))

    pca = PCA(n_components=2)

    components = pca.fit_transform(scaled)

    pca_df = pd.DataFrame({
        "PCA1": components[:,0],
        "PCA2": components[:,1],
        "Cluster": df["cluster"]
    })

    plt.figure(figsize=(8,6))

    sns.scatterplot(
        data=pca_df,
        x="PCA1",
        y="PCA2",
        hue="Cluster",
        palette="viridis",
        alpha=0.8
    )

    plt.title("Cluster Segmentation (PCA Projection)")
    plt.xlabel("Principal Component 1")
    plt.ylabel("Principal Component 2")

    plt.legend(title="Cluster Group")

    plt.tight_layout()
    cluster_counts = df["cluster"].value_counts()

    print("Cluster distribution:")
    print(cluster_counts)

    filename = "cluster_pca.png"
    plt.savefig(os.path.join(output_dir, filename))

    plt.close()

def select_important_features(df, max_features=6):

    numeric = df.select_dtypes(include=["number"]).copy()

    # Remove constant columns
    numeric = numeric.loc[:, numeric.std() > 0]

    # Remove ID-like columns
    drop_cols = [col for col in numeric.columns if "id" in col.lower() or "isbn" in col.lower()]
    numeric = numeric.drop(columns=drop_cols, errors="ignore")

    if numeric.empty:
        return []

    # Variance score
    variance = numeric.var()

    # Correlation score (how connected feature is to others)
    corr = numeric.corr().abs()
    corr_score = corr.mean()

    # Combined score
    score = variance * corr_score

    # Sort and select top features
    important_cols = score.sort_values(ascending=False).head(max_features).index.tolist()

    return important_cols

# VISUALIZATION GENERATION

def create_visualizations(df, output_dir):

    important_cols = select_important_features(df)
    numeric = df[important_cols]
    categorical = df.select_dtypes(include=["object","string"])

    # Correlation heatmap

    if len(important_cols) >= 2:

        numeric = df[important_cols]

        corr = numeric.corr()

        plt.figure(figsize=(8,6))

        sns.heatmap(
            corr,
            cmap="coolwarm",
            center=0,
            linewidths=0.5,
            cbar=True,
            annot=True
        )

        plt.title("Correlation Heatmap (Key Features)")

        plt.xticks(rotation=45, ha="right")
        plt.yticks(rotation=0)

        plt.tight_layout()

        filename = "correlation_heatmap.png"
        plt.savefig(os.path.join(output_dir, filename))

        plt.close()

    # Distribution plots
    for col in important_cols[:2]:

        plt.figure()

        sns.histplot(df[col], kde=True)

        plt.title(f"Distribution of {col}")

        plt.tight_layout()
        safe_col = clean_name(col)
        filename = f"distribution_{safe_col}.png"
        plt.savefig(os.path.join(output_dir, filename))

        plt.close()

    # Boxplots
    for col in important_cols[:2]:

        # If numeric column has few unique values → treat like categorical
        if df[col].nunique() <= 10 and df[col].min() >= 1 and df[col].max() <= 5:

            sns.countplot(
                x=df[col],
                hue=df[col],
                palette="viridis",
                legend=False
            )

            plt.title(f"Distribution of '{col}' (unique values: {df[col].nunique()})")
            plt.xlabel(f"{col} values")
            plt.ylabel("Frequency (number of records)")
            safe_col = clean_name(col)
            filename = f"categorical_from_numeric_{safe_col}.png"
            plt.savefig(os.path.join(output_dir, filename))

        else:

            sns.boxplot(x=df[col], color="skyblue")

            plt.title(f"Outliers in {col}")
            plt.xlabel(col)
            safe_col = clean_name(col)
            filename = f"boxplot_{safe_col}.png"
            plt.savefig(os.path.join(output_dir, filename))

        plt.tight_layout()

        

        plt.close()

    # Missing values heatmap
    missing_counts = df.isnull().sum()

# Only proceed if missing values exist
    if missing_counts.sum() > 0:

        # Focus only on columns that actually have missing values
        missing_cols = missing_counts[missing_counts > 0].index

        plt.figure(figsize=(10,5))

        sns.heatmap(
            df[missing_cols].isnull(),
            cbar=False,
            yticklabels=False,
            cmap="viridis"
        )

        plt.title("Missing Data Pattern (Only Columns with Missing Values)")

        plt.xlabel("Columns")

        plt.tight_layout()

        filename = "missing_heatmap.png"
        plt.savefig(os.path.join(output_dir, filename))
        plt.close()

    # Categorical distributions
   # Select only top 2 useful categorical columns
    valid_cats = []

    for col in categorical.columns:

        counts = df[col].value_counts()

        # Skip useless columns
        if counts.max() <= 1:
            continue

        if counts.nunique() <= 1:
            continue

        if len(counts) > 15:
            continue

        if "id" in col.lower() or "isbn" in col.lower() or "url" in col.lower():
            continue

        valid_cats.append((col, counts.var()))

    # Sort by variability (more variation = more useful)
    valid_cats = sorted(valid_cats, key=lambda x: x[1], reverse=True)

    # Take top 2
    for col, _ in valid_cats[:2]:

        top = df[col].value_counts().head(10)

        plt.figure(figsize=(8,5))

        sns.barplot(
            x=top.values,
            y=top.index,
            hue=top.index,
            palette="viridis",
            legend=False
        )

        plt.title(f"Top Categories in '{col}'")
        plt.xlabel("Frequency")
        plt.ylabel(col)

        plt.tight_layout()

        safe_col = clean_name(col)
        filename = f"categorical_{safe_col}.png"

        plt.savefig(os.path.join(output_dir, filename))

        plt.close()

def scatter_strong_correlations(df, output_dir):

    important_cols = select_important_features(df)
    numeric = df[important_cols]

    if len(numeric.columns) < 2:
        return

    corr = numeric.corr().abs()

    pairs = []

    for i in corr.columns:
        for j in corr.columns:

            if i != j:

                pairs.append((i, j, corr.loc[i, j]))

    # sort by correlation strength
    pairs = sorted(pairs, key=lambda x: x[2], reverse=True)

    plotted = set()
    count = 0

    for col1, col2, value in pairs:

        if count >= 2:
            break

        if (col2, col1) in plotted:
            continue

        if value < 0.5:
            continue

        plt.figure(figsize=(7,5))

        sns.scatterplot(
            x=df[col1],
            y=df[col2],
            alpha=0.6
        )

        plt.title(f"{col1} vs {col2} (Strong Relationship)")
        plt.xlabel(col1)
        plt.ylabel(col2)

        plt.tight_layout()

        safe_x = clean_name(col1)
        safe_y = clean_name(col2)

        filename = f"scatter_{safe_x}_vs_{safe_y}.png"

        plt.savefig(os.path.join(output_dir, filename))

        plt.close()

        plotted.add((col1, col2))

        count += 1

# GETTING INSIGHTS FROM VISUALIZATIONS( TO CUT DOWN THE COST OF SENDING IMAGES TO LLM)

def visualization_insights(df):

    numeric = df.select_dtypes(include=["number"])

    insights = {}

    if len(numeric.columns) > 0:

        insights["highest_variance_features"] = (
            numeric.var().sort_values(ascending=False).head(5).to_dict()
        )

    if len(numeric.columns) > 1:

        corr = numeric.corr().abs()

        corr_pairs = []

        for i in corr.columns:
            for j in corr.columns:

                if i < j and corr.loc[i,j] > 0.7:

                    corr_pairs.append((i,j,round(corr.loc[i,j],2)))

        insights["strong_correlations"] = corr_pairs[:5]

    return insights

# LLM SUGGESTED ANALYSIS(FOR BETTER INTERPRETATION OF DATA PATTERNS)
def ask_llm_for_analysis(summary, correlations, outliers):

    try:

        client = get_llm()

        prompt = f"""
You are a senior data scientist reviewing results from automated
exploratory data analysis.

Based on the dataset structure below, recommend up to 3 additional analyses
that could reveal deeper insights.

Dataset shape: {summary["shape"]}

Numeric columns:
{summary["numeric_columns"]}

Categorical columns:
{summary["categorical_columns"]}

Strong correlations:
{correlations}

Outliers:
{outliers}



Focus on analyses that could reveal:
• hidden patterns
• important drivers
• anomalies
• segmentation opportunities

Return JSON only:

[
{{"analysis":"analysis name","description":"insight"}}
]
"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  
            messages=[{"role": "user", "content": prompt}]
        )

        text = response.choices[0].message.content

        match = re.search(r"\[.*\]", text, re.DOTALL)

        if match:
            return json.loads(match.group())

        return json.loads(text)

    except Exception as e:

        print("LLM suggestion failed:", e)

        return []

# ExecuteS suggested analysis

def execute_dynamic_analysis(df, suggestions):

    results = []
    numeric = df.select_dtypes(include=["number"])

    for s in suggestions:

        name = s["analysis"].lower()

        #  FEATURE IMPORTANCE
        if "feature" in name or "importance" in name:
            if len(numeric.columns) > 1:
                importance = numeric.corr().abs().mean().sort_values(ascending=False)
                results.append({
                    "analysis": "Feature Importance",
                    "result": importance.head(5).to_dict()
                })

        #  DISTRIBUTION
        elif "distribution" in name:
            results.append({
                "analysis": "Distribution Summary",
                "result": numeric.describe().to_dict()
            })

        #  CLUSTERING INSIGHTS
        elif "cluster" in name:
            if "cluster" in df.columns:
                cluster_info = df["cluster"].value_counts().to_dict()
                results.append({
                    "analysis": "Cluster Analysis",
                    "result": cluster_info
                })

        #  ANOMALY DETECTION 
        elif "anomaly" in name:
            from sklearn.ensemble import IsolationForest

            if len(numeric.columns) > 1:
                model = IsolationForest(contamination=0.05, random_state=42)
                preds = model.fit_predict(numeric.fillna(0))

                anomaly_count = (preds == -1).sum()

                results.append({
                    "analysis": "Anomaly Detection",
                    "result": f"{anomaly_count} anomalies detected"
                })
        # PCA ANALYSIS
        elif "pca" in name or "dimensionality" in name or "reduction" in name:

            from sklearn.decomposition import PCA
            from sklearn.preprocessing import StandardScaler

            if len(numeric.columns) > 1:

                scaler = StandardScaler()
                scaled = scaler.fit_transform(numeric.fillna(0))

                pca = PCA()
                pca.fit(scaled)

                explained_variance = pca.explained_variance_ratio_

                results.append({
                    "analysis": "PCA Analysis",
                    "result": {
                        "explained_variance_ratio": explained_variance[:5].round(3).tolist(),
                        "total_variance_explained": round(explained_variance[:2].sum(), 3)
                    }
                })
        # TIME SERIES ANALYSIS
        elif "time" in name or "trend" in name or "season" in name:

            # try to find datetime column
            time_col = None

            for col in df.columns:
                if "date" in col.lower() or "time" in col.lower() or "year" in col.lower():
                    try:
                        df[col] = pd.to_datetime(df[col], errors="coerce")
                        time_col = col
                        break
                    except:
                        continue

            if time_col:

                # pick one important numeric column
                numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

                if numeric_cols:
                    target = numeric_cols[0]

                    ts = df[[time_col, target]].dropna().sort_values(time_col)

                    if len(ts) > 5:

                        trend = ts[target].diff().mean()

                        results.append({
                            "analysis": "Time Series Trend Analysis",
                            "result": {
                                "time_column": time_col,
                                "target_variable": target,
                                "trend_direction": "increasing" if trend > 0 else "decreasing",
                                "average_change": round(float(trend), 3)
                            }
                        })

        #  GENERIC FALLBACK 
        else:
            results.append({
                "analysis": name,
                "result": "Indicates potential deeper structure in the dataset and suggests further modeling opportunities that can be implemented if needed."
            })

    return results


# REPORT GENERATION BY LLM
def generate_report(summary, correlations, outliers, viz, cluster_info, dynamic_results):

    try:

        client = get_llm()

        prompt = f"""
You are a senior data scientist preparing a high-impact  and high-quality analytical report.

Your goal is to extract **actionable insights**, not describe obvious statistics.
IMPORTANT:
- Do NOT describe data — INTERPRET it
- Avoid generic statements
- Every insight must include:
  Observation → Interpretation → Implication

DATASET SUMMARY

Rows: {summary["shape"][0]}
Columns: {summary["columns"]}

Numeric Features:
{summary["numeric_columns"]}

Categorical Features:
{summary["categorical_columns"]}

Missing Values:
{summary["missing_values"]}

Statistical Summary:
{summary["summary_statistics"]}

Strong Correlations:
{correlations}

Outliers:
{outliers}

Cluster Distribution:
{cluster_info}

Visualization Insights:
{viz}

Additional analysis:
{dynamic_results}


STRICT INSTRUCTIONS (VERY IMPORTANT)
1. DO NOT repeat raw numbers unless necessary.
2. DO NOT write generic statements like:
   - "data shows variability"
   - "there are correlations"
3. ALWAYS explain:
   - WHY something is happening
   - WHAT it implies
   - HOW it can be used

4. Focus on:
   - patterns
   - anomalies
   - relationships
   - business meaning

5. Every insight must follow this structure:
   Observation → Interpretation → Implication (each insight as one paragraph,and each insight must be ordered like 1,2,3...so on)
   - No generic phrases
   - No repetition
   - Be specific and analytical
   - Prioritize insights over description

6.FORBIDDEN PHRASES LIKE(be specific to given data):
   - "data shows"
   - "there are patterns"
   - "it can be observed"
   - "indicates variability"


REPORT STRUCTURE
# Automated Data Analysis Report

## 1. Dataset Overview
Explain what kind of dataset this appears to be and its structure.

## 2. Data Quality Assessment
Identify real issues (missing data, inconsistencies, skewness).

## 3. Key Patterns in Data
Explain important distributions and what they mean.

## 4. Feature Relationships
Interpret strongest correlations and why they exist.(explain WHY correlations exist)

## 5. Outlier Analysis
what they represent in real-world
Explain what unusual values indicate (errors, rare events, high performers).

## 6. Segmentation / Clustering Insights
Explain what each cluster likely represents in real-world terms.

## 7. Key Insights (CRITICAL SECTION)
Write 4–6 sharp, non-obvious insights.

## 8. Strategic Implications
Translate insights into decisions (marketing, product, optimization).

## 9. Business Implications
(what decisions can be made)


## 10. Recommendations
Suggest next steps (ML models, feature engineering, data collection).

STYLE REQUIREMENTS

• Write like a professional data scientist
• Avoid generic filler sentences
• Be specific and analytical
• Use clear, structured paragraphs
• Make it useful for decision-makers

Return ONLY Markdown.
"""

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}]
        )
        if len(response.choices[0].message.content) < 200:
            return "# Analysis generated limited insights. Please review dataset."

        return response.choices[0].message.content
    

    except Exception as e:

        print("LLM report failed:", e)

        return "# Automated Dataset Analysis\n\nReport generation failed."
    
def rank_images(images):
    ranked = []

    for img in images:
        score = 0
        name = img.lower()

        # HIGH VALUE charts
        if "scatter" in name or "vs" in name:
            score += 5   # relationships (VERY important)

        if "correlation" in name:
            score += 5   # core insight

        if "cluster_pca" in name:
            score += 5   # segmentation

        if "missing" in name:
            score += 4   # data quality

        # MEDIUM VALUE
        if "distribution" in name:
            score += 3

        if "boxplot" in name:
            score += 3

        # LOW VALUE (supporting)
        if "categorical" in name:
            score += 2

        ranked.append((img, score))

    # sort by score descending
    ranked = sorted(ranked, key=lambda x: x[1], reverse=True)

    selected = []
    types_used = set()

    for img, score in ranked:
        name = img.lower()

        if "scatter" in name and "scatter" not in types_used:
            selected.append(img)
            types_used.add("scatter")

        elif "heatmap" in name and "heatmap" not in types_used:
            selected.append(img)
            types_used.add("heatmap")

        elif "cluster" in name and "cluster" not in types_used:
            selected.append(img)
            types_used.add("cluster")

        elif "boxplot" in name and "boxplot" not in types_used:
            selected.append(img)
            types_used.add("boxplot")

        elif "distribution" in name and "distribution" not in types_used:
            selected.append(img)
            types_used.add("distribution")

        elif "categorical" in name and "categorical" not in types_used:
            selected.append(img)
            types_used.add("categorical")

        # stop when we have enough
        if len(selected) == 6:
            break

    return selected
        
# README GENERATION

def create_readme(text, output_dir, dynamic_results):

    readme_path = os.path.join(output_dir, "README.md")

    with open(readme_path, "w", encoding="utf-8") as f:

        f.write("# Automated Data Analysis Report\n\n")

        f.write(text)

        f.write("\n\n## Advanced LLM-Driven Analysis\n\n")

        for item in dynamic_results:
            f.write(f"### {item['analysis']}\n")
            if isinstance(item["result"], dict):
                for k, v in item["result"].items():
                    if isinstance(v, (int, float)):
                        f.write(f"- {k}: {round(v,2)}\n")

                    elif isinstance(v, dict):
                        f.write(f"- {k}:\n")
                        for sub_k, sub_v in v.items():
                            if isinstance(sub_v, (int, float)):
                                f.write(f"  - {sub_k}: {round(sub_v,2)}\n")
                            else:
                                f.write(f"  - {sub_k}: {sub_v}\n")

                    else:
                        f.write(f"- {k}: {v}\n")
            else:
                f.write(f"{item['result']}\n")

            f.write("\n")

        f.write("\n\n## Interpretation of Visual Evidence\n\n")
        f.write(
        "The following visualizations support and validate the analytical findings discussed above, "
        "highlighting key distributions, relationships, and segmentation patterns.\n\n"
        )
        
        f.write("\n\n## Visualizations\n\n")

        images = sorted(
            [img for img in os.listdir(output_dir) if img.endswith(".png")]
        )
        images = rank_images(images) 
        images = images[:6]

        for img in images:

            title = img.replace("_", " ").replace(".png", "").title()
        
            f.write(f"### {title}\n\n")
            
        
            # description logic
            if "scatter" in img or "vs" in img:
                desc = "This scatter plot shows the relationship between two key variables, helping identify correlation patterns or trends."
        
            elif "correlation" in img:
                desc = "This heatmap highlights strong relationships between numerical features, indicating which variables move together."
        
            elif "cluster" in img:
                desc = "This visualization represents clustering results, showing how data points are grouped based on similarity."
        
            elif "boxplot" in img:
                desc = "This boxplot highlights the distribution of values and helps identify potential outliers in the dataset."
        
            elif "distribution" in img:
                desc = "This plot shows how values are distributed, revealing skewness, spread, and concentration."
        
            elif "categorical" in img:
                desc = "This chart shows frequency distribution of categorical variables, helping understand dominant categories."
        
            elif "missing" in img:
                desc = "This heatmap reveals missing data patterns across features, helping identify data quality issues."
        
            else:
                desc = "This visualization provides additional perspective on the dataset."
        
            f.write(f"{desc}\n\n")
            f.write(f"![{title}]({img})\n\n")

# MAIN PIPELINE

def main():

    if len(sys.argv) < 2:
       print("Usage: uv run autolysis.py <dataset.csv>")
       return

    file = sys.argv[1]

    dataset_name = os.path.splitext(os.path.basename(file))[0]

    output_dir = dataset_name

    os.makedirs(output_dir, exist_ok=True)

    df = load_dataset(file)

    summary = basic_analysis(df)

    correlations = correlation_analysis(df)

    outliers = detect_outliers(df)

    df = cluster_analysis(df)
    cluster_info = df["cluster"].value_counts().to_dict() if "cluster" in df.columns else {}

    create_visualizations(df, output_dir)

    scatter_strong_correlations(df, output_dir)

    pca_visualization(df, output_dir)

    viz_insights = visualization_insights(df)

    suggestions = ask_llm_for_analysis(summary, correlations, outliers)

    dynamic_results = execute_dynamic_analysis(df, suggestions)

    report = generate_report(summary, correlations, outliers, viz_insights, cluster_info, dynamic_results)
    if not report or len(report) < 300:
        report = "# Automated Data Analysis\n\nInsights could not be fully generated. Review dataset."
    create_readme(report, output_dir, dynamic_results)

    print("Analysis completed successfully.")


if __name__ == "__main__":
    main()