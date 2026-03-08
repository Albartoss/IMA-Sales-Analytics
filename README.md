===========================================================================
PROJECT: INVENTORY MANAGEMENT ASSISTANT WITH SALES & PROFITABILITY ANALYSIS
===========================================================================

DEVELOPER INFORMATION:
----------------------
Name-Surname     : Yigit Ayik
Degree           : B.Sc. Software Engineering
Institution      : National Technical University of Ukraine "KPI" (2025)
Project Advisor  : Assoc. Prof. Volodymyr Shymkovych

1. PROJECT OVERVIEW
-------------------
This project is an end-to-end software solution designed to modernize inventory
tracking and optimize business decision-making through predictive analytics. 
The system integrates traditional stock management with machine learning-based 
forecasting models to predict future sales trends and profitability.

2. CORE FUNCTIONALITIES
-----------------------
- Automated Inventory Tracking: Real-time stock updates and barcode integration.
- Predictive Analytics: Future demand forecasting using Prophet and ARIMA models.
- Financial Reporting: Detailed profitability analysis and sales trend visualization.
- Multi-User System: Role-Based Access Control (Admin, Owner, Worker).
- Localization: Multi-language support (English, Turkish, Ukrainian).

3. TECHNICAL SPECIFICATIONS
---------------------------
- Programming Language  : Python 3.10+
- Graphical User Interface: PyQt5
- Database Management    : SQLite3 (Structured Query Language)
- Data Science Libraries : Pandas, NumPy, Scikit-learn
- Forecasting Engines    : Facebook Prophet, Statsmodels (ARIMA)
- Visualization          : Plotly, Matplotlib

4. SYSTEM ARCHITECTURE
----------------------
The software follows a Layered Architectural Pattern to ensure scalability:
- UI Layer       : Handles user interactions and data presentation.
- Business Layer : Processes inventory logic and runs ML algorithms.
- Data Layer     : Manages persistent storage and database queries.

5. IMPLEMENTED ML MODELS
------------------------
- Prophet Model : Applied for handling long-term seasonality and holiday effects.
- ARIMA Model   : Implemented for short-term statistical time-series forecasting.
The combination of these models provides a robust decision-support mechanism 
for stock optimization.

6. HOW TO DEPLOY
----------------
1. Ensure Python 3.10 or higher is installed.
2. Install dependencies: 'pip install -r requirements.txt'
3. Execute the application: 'python main.py'

7. ACADEMIC CONTEXT
-------------------
This system was developed as a Bachelor’s Graduation Project in the 
"Computer Systems Software Engineering" department. It was formally 
defended and approved by the Faculty of Informatics and Computer Engineering 
at NTUU "Igor Sikorsky Kyiv Polytechnic Institute" in 2025.

---------------------------------------------------------------------------
For further technical inquiries, please refer to the full PDF documentation.
===========================================================================

Admin account: Yigit - 3535
Owner account: Owner - 123
Personal account: Personal - 123
