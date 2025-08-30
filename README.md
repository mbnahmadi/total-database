# total-database

This project is a high-performance **weather and wave data management system** built with Django and PostgreSQL/PostGIS.  
It is designed to handle **large-scale geospatial and temporal datasets**, with fast data import, querying, and API access for weather and oceanographic applications.

---

## Key Features

### Database Design & Data Flow
- **PostGIS database** for geospatial data.
- Separate tables for **active** and **backup** data:
  - Active table holds the most recent 12 hours of data.
  - Data in the active table is refreshed every 12 hours.
  - Backup table stores historical data, which is never deleted.
- Data is imported from **NetCDF (`.nc`) and CSV files**.
- Uses **`djangopostgrescopy`** for high-performance bulk inserts (~3 million records in <3 minutes).
- Indexed and clustered tables for **high-speed queries**.

### API Layer
- Provides endpoints for:
  - Retrieving data from the **nearest point** within a time range.
  - Retrieving data for a **spatial area** within a time range.
- Supports **pagination** for large query results.

### High Performance & Scalability
- Celery integration for **scheduled data ingestion** and processing.
- Optimized database operations with **bulk copy**, **indexes**, and **clustering**.
- Designed for **large-scale weather and oceanographic datasets**.

---

## Technology Stack
- **Backend:** Django, Django REST Framework
- **Database:** PostgreSQL + PostGIS
- **Data Import:** NetCDF, CSV
- **Performance:** djangopostgrescopy, Indexing, Clustering
- **Task Queue:** Celery

---

## In Progress / Upcoming Features
Full integration with Celery for automated data ingestion.
Advanced spatial and temporal query endpoints.
Optional data export functionality with filtering and pagination.
Performance optimizations for extremely large datasets.