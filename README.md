# Environment Agency (EA) API Comparer

Welcome to the EA API Comparer! This application allows you to search for UK Environment Agency monitoring stations, track river levels and rainfall, and visually compare continuous data trends over time.

## Prerequisites

To run this application, you will need to have **Python** installed on your computer. If you don't have it installed, you can download it from [python.org](https://www.python.org/downloads/).

## Getting Started

Follow these steps to get the app running on your own machine.

### 1. Download the Application

First, you need to download this repository to your computer. Open your terminal (or Command Prompt / PowerShell on Windows) and run:

```bash
git clone <YOUR-GITHUB-REPO-URL>
cd "EA API comparer"
```
*(Note: Replace `<YOUR-GITHUB-REPO-URL>` with the actual link to your GitHub repository once published)*

### 2. Set Up a Virtual Environment (Recommended)

It's a best practice in Python to create a "virtual environment" so the app's requirements don't interfere with other projects on your computer.

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On Mac/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install the Requirements

Now that your environment is ready, install the necessary libraries that power the app:

```bash
pip install -r requirements.txt
```

### 4. Run the App!

Finally, start the application using Streamlit:

```bash
streamlit run app.py
```

A browser window should automatically pop up showing the application. If it doesn't, you can copy the "Local URL" printed in your terminal (usually `http://localhost:8501`) and paste it into your web browser.

## Features

- **Search by Text or Location**: Find monitoring stations by their name, river, or even by geographic location mapping using a radius from a local town or postcode.
- **Dynamic Comparisons**: Select multiple stations and measures (like Rainfall, Flow, or Water Levels).
- **Split Graphing**: Automatically aligns the plot to correctly separate complex data formats (like overhead inverted Rainfall bars vs continuous rising water levels).
- **Interactive Mapping**: Provides an interactive map outlining your search radius and the hardware stations you are currently visualizing.
