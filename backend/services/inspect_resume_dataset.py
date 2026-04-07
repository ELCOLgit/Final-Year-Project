import os

import pandas as pd


def main():
    # build the csv path relative to this file
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    csv_path = os.path.join(project_root, "backend", "data", "Resume.csv")

    # load the resume dataset
    resume_data = pd.read_csv(csv_path)

    # print the dataset columns
    print("columns:")
    for column_name in resume_data.columns:
        print(column_name)

    # print the first 3 rows
    print("\nfirst 3 rows:")
    print(resume_data.head(3))


if __name__ == "__main__":
    main()
