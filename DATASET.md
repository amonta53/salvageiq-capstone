# Dataset Access

Due to GitHub file size limitations, the full dataset is hosted externally.

## Download

[SalvageIQ_Full_Dataset_2026_04.zip](https://drive.google.com/file/d/1yScGJGDeJSLKisI25edEak4WMOHsN9uH/view?usp=sharing)

## Structure
```text
└── data/
    └── runs/
        └── f6a9bce2-e6a8-491b-96ee-e66206bcddf4/
            ├── raw/
            │   └── raw_listings.csv
            ├── processed/
            │   ├── cleansed_listings.csv
            │   ├── normalized_listings.cs
            │   └── market_summary.csv
            └── outputs/
                └── analysis/
                    ├── analysis_summary.csv
                    ├── ranked_parts_all.csv
                    └── ranked_parts_top10.csv
```

## Reproducibility

Run the pipeline locally using:

python main.py full