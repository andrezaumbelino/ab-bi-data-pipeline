# 📊 Pipedrive BI Data Pipeline

This repository contains a structured data pipeline project built to extract data from the Pipedrive API and load it into Google BigQuery for Business Intelligence analysis.

The goal of this project is to build a scalable and professional data architecture that supports dashboard development in Looker Studio and advanced BI analysis.

This repository serves as a portfolio project showcasing real-world data engineering practices applied to CRM data.

---

## ✅ Project Overview

### 1. Pipedrive to BigQuery Pipeline  
Folder: pipedrive_bi

Description:  
A modular Python pipeline that extracts data from the Pipedrive REST API and loads it into BigQuery using structured data layers.

### Key Features:

- API connection with automatic pagination handling  
- Secure environment variable configuration (.env)  
- Modular project structure (config, API client, BigQuery loader)  
- Raw data ingestion layer in BigQuery  
- Support for TRUNCATE and UPSERT strategies  
- Designed for scalability and automation  

---

## 🧠 Data Architecture

Pipedrive API
↓
Python (Extraction & Normalization)
↓
BigQuery - Raw Layer
↓
SQL Transformations (Staging / Dim / Fact)
↓
Looker Studio Dashboards

---

# 📊 Dashboard Previews

Dashboard Gallery: [View Here](./assets)

The dashboards were built using **simulated and anonymized data** for portfolio purposes only.

All datasets were generated to demonstrate:

- Business logic implementation
- CRM performance analysis
- Data modeling best practices
- Visualization design principles

No real company data is exposed.

---

## 🛠️ Tools & Technologies

- Python  
- Pipedrive REST API  
- Google BigQuery  
- Pandas  
- SQL  
- Looker Studio  
- Git & GitHub  

---

## 👩🏾‍💻 About Me

Hi! I'm **Andreza Umbelino**,  
Business Intelligence Specialist at Atlantic Bridge.

This project represents my work in building scalable BI data pipelines, transforming raw CRM data into structured datasets ready for analytics and dashboard development.

I focus on creating clean architectures, efficient data flows, and reliable data models that support decision-making processes.

---

📌 Connect with me:

🔗 [LinkedIn](https://www.linkedin.com/in/andrezaumbelino/)

