# llm-autodata-analysis
An LLM-Driven Automated Data Analysis System
LLM-Driven Automated Data Analysis System
Overview

This project implements an intelligent data analysis pipeline that combines traditional exploratory data analysis (EDA) with Large Language Models (LLMs) to generate actionable insights.

The system automatically:

1.Performs dataset analysis
2.Generates meaningful visualizations
3.Uses LLMs to suggest advanced analyses
4.Executes selected analyses dynamically
5.Produces professional analytical reports

Key Features:
1. Automated EDA
Statistical summaries
Missing value analysis
Correlation detection
Outlier detection
2. Intelligent Visualizations
Correlation heatmaps
Distribution plots
Boxplots for outliers
PCA-based cluster visualization
3. LLM-Guided Analysis
Suggests additional analyses dynamically
Executes selected analyses (feature importance, clustering, anomaly detection)
Generates professional reports
4. Dataset-Specific Reports

Each dataset generates:

A detailed README.md
Relevant visualizations

How to Run
uv run autolysis.py dataset.csv

Example:

uv run autolysis.py goodreads.csv

Technologies Used:

1.Python
2.Pandas
3.Scikit-learn
4.Seaborn / Matplotlib
5.LLM (Groq)

Key Innovation:

This project goes beyond static analysis by introducing:

LLM-guided dynamic analytics, where:

The model suggests new analytical directions
The system executes them automatically
Results are incorporated into insights

Output

For each dataset:

Structured Markdown report
Visual insights
Advanced analysis results

