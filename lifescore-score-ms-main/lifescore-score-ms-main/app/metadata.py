"""
This module contains the metadata for the LifeScore Scoring Microservice API.
"""

openapi_tags = [
    {
        "name": "Scoring",
        "description": """
        Score calculation and management operations including domain-specific scores,
        overall LifeScore computation, and weekly report generation. Handles the
        complete scoring lifecycle for all supported domains:
        - State of Mind
        - Food
        - Nutrition
        - Sleep
        - Spiritual
        - Fitness
        - Morale
        - Cohesion
        - Social
        """,
    }
]

APP_DESCRIPTION = """
# LifeScore Scoring Microservice API Documentation

## Overview
Specialized microservice for calculating and managing LifeScore metrics across multiple
domains. Provides endpoints for score calculation, weekly report generation, and score
retrieval operations.

## Core Functionalities

### 1. Domain Score Calculation
- Individual domain score computation
- Weighted scoring algorithms
- Historical data consideration
- Temporal decay factors
- Custom scoring parameters per domain

### 2. LifeScore Computation
- Weighted domain aggregation
- Normalized scoring (0-100 scale)
- Domain-specific weight factors:
  - State of Mind: 1.008
  - Sleep: 1.008
  - Spiritual: 0.84
  - Nutrition: 1.014
  - Food: 1.056
  - Fitness: 1.074

### 3. Report Generation
- Weekly report creation
- Initial assessment reports
- Historical score tracking
- Report persistence
- Score comparison analytics

### 4. Score Management
- Score retrieval by domain
- User-specific scoring
- Score persistence
- Profile score updates
- Task generation based on scores

## Technical Details

### API Structure
- RESTful architecture
- Domain-specific endpoints
- Secure authentication
- Comprehensive error handling
- Detailed logging

### Performance Features
- Efficient score calculation
- Caching mechanisms
- Batch processing support
- Optimized database queries

### Integration Points
- User authentication
- Profile management
- Task generation
- Resource recommendations

## Usage Guidelines

### Authentication
Protected endpoints require JWT token:
```
Authorization: Bearer <jwt_token>
```

### Response Format
Standard JSON response structure:
```json
{
    "data": {
        "domain_scores": {
            "STATE_OF_MIND": 85.5,
            "SLEEP": 90.0,
            "SPIRITUAL": 75.5,
            "NUTRITION": 88.0,
            "FOOD": 82.5,
            "FITNESS": 79.0
        },
        "life_score": 83.5
    },
    "message": "Scores calculated successfully",
    "status_code": 200
}
```

## Support & Resources
- Technical Documentation: docs.lifescore.com/scoring
- API Support: api-support@lifescore.health
- Status Page: status.lifescore.com
"""

__all__ = ["openapi_tags", "APP_DESCRIPTION"]
