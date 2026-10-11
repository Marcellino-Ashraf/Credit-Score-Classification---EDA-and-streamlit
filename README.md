# Credit Score Classification: EDA & Analytics Dashboard

Exploratory data analysis and a multi-page Streamlit dashboard built on the
[Credit Score Classification dataset (Kaggle)](https://www.kaggle.com/datasets/parisrohan/credit-score-classification).
The data holds the banking and credit profile of 12,500 customers, one record per customer per month
(January to August), and the credit score the bank gave them: **Poor**, **Standard** or **Good**.

Only `train.csv` is used: `test.csv` has no `Credit_Score` column, so it cannot answer questions about the score.

## Project Structure

```
├── Credit Score Classification - EDA.ipynb   # Cleaning, univariate, bivariate analysis and 6 questions
├── train.csv                                  # Raw data (Kaggle)
├── cleaned_data.parquet                       # Output of the notebook, read by the app
├── app.py                                     # Streamlit entry point: page config, navigation, CSS
├── .env                                       # GEMINI_API_KEY (git-ignored, not committed)
├── pages/
│   ├── overview.py              # Headline KPIs, score distribution, column dictionary
│   ├── univariate_analysis.py   # Distribution of every column (optionally split by score)
│   ├── score_drivers.py         # Any variable vs credit score
│   ├── occupation_insights.py   # Score mix, income and debt per occupation
│   ├── analysis_questions.py    # The 6 notebook questions, recalculated for the filters
│   └── voice_assistant.py       # Gemini Live voice assistant (professional Egyptian Arabic) that shows KPIs and charts
├── utils/
│   ├── components.py   # Global CSS loader + header helpers for the Voice Assistant
│   └── voice_visuals.py # Tools Gemini calls to show KPIs and charts during the conversation
├── assets/             # style.css, voice_widget.html, credit_score.svg (overview image)
├── .streamlit/config.toml
└── requirements.txt
```

## Data Cleaning (summary)

| Problem | Fix |
| --- | --- |
| Numbers stored as text with `_` (Age, Annual_Income, Num_of_Loan, ...) | Removed `_`, converted to numbers |
| Garbage / placeholder values (`_______`, `!@9#%8`, `_`, `__10000__`, `-3.3e+26`) | Treated as missing |
| Missing values | Filled from the **same customer's** other months (mode for categories, median for numbers) |
| Impossible values (age 8698, 1,499 credit cards, interest rate 5,797%, ...) | Replaced by the customer's usual value |
| Num_of_Loan < 0 or > 10 (4.3% of rows) | Rows dropped |
| `Credit_History_Age` as text (`22 Years and 1 Months`) | New numeric column `Credit_History_Age_months` |
| Name, SSN | Dropped (not useful) |

Result: 95,652 rows, 27 columns, no missing values, no duplicates.

## Analysis Questions

1. Does the occupation of a customer affect the credit score?
2. Do customers with higher income get better credit scores?
3. How does late payment behaviour relate to the credit score?
4. How do outstanding debt and interest rate differ between credit score groups?
5. Does having more credit cards, bank accounts or loans lead to a worse credit score?
6. Does a longer credit history and a better credit mix mean a better credit score?

**Main findings:** occupation has only a very weak link with the score (26-31% Poor in every job).
Credit mix, paying only the minimum amount, days late, outstanding debt, interest rate, number of credit
products and credit history age separate Poor from Good customers clearly.

## Getting Started

```bash
# activate your environment (e.g. conda activate ML), then:
pip install -r requirements.txt
streamlit run app.py
```

The Voice Assistant page reads `GEMINI_API_KEY` from the `.env` file (git-ignored). Each analysis page is self-contained: it imports only pandas, plotly.express and streamlit.

If `cleaned_data.parquet` is missing, run the notebook top to bottom first: its last cleaning step writes it.
