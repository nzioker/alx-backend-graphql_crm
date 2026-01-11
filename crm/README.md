# Celery Task Setup for CRM Reports

This guide explains how to set up Celery with Celery Beat for generating automated CRM reports using GraphQL queries.

## Prerequisites

- Python 3.8+
- Django 4.2+
- Redis server
- Running Django application with GraphQL endpoint

## Installation Steps

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Or install individually
pip install celery django-celery-beat redis gql requests django-celery-results
