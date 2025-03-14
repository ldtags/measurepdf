
# Measure Summary Generator

To update the section descriptions, generate a new section_descriptions.json file by using the section_builder script.
To update the sunsetted measures, generate a new sunsetted_measures.json file by using the section_builder script.


## Specs

Python 3.11.9


## Usage

./cli.py build [options]

options:
  -m, --measures <*str>         Zero or more measures to add to the generated summary
  -u, --use-categories <*str>   Zero or more use categories to filter measures by
  -o, --output-file <str>       Specifies the file path to the output file
  -a, --all                     If included, all measures that satisfy the specified constraints will be added
  -l, --limit <int>             Specifies the maximum number of measures to include in the summary
  --min-start-date <date>       Specifies the minimum start date (inclusive) for measures in the summary
  --max-start-date <date>       Specifies the maximum start date (non-inclusive) for measures in the summary
  --min-end-date <date>         Specifies the minimum end date (inclusive) for measures in the summary
  --max-end-date <date>         Specifies the maximum end date (non-inclusive) for measures in the summary
