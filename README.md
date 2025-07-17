# 📘 Module Summary

## Title: REST API for Field Service Integration in Odoo

### Description:
This module provides a RESTful API interface to expose selected data from the Field Service module in Odoo. It is designed to enable external applications (such as mobile or web clients) to securely consume and interact with intervention-related data, such as work orders, scheduling, priorities, and assigned clients.

Key Features:

- Exposes data from the project.task model used by Field Service

- Returns only essential fields 

- Custom HTTP endpoints for filtered and secure access

- Token-based authentication for API access