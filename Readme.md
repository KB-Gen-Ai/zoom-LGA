# Zoom Al Arab — KSA Opportunity Intelligence

Lead-generation and opportunity-intelligence agent for Zoom Al Arab General Contracting Company.

## Purpose

Identify Saudi Arabian procurement, tender, project, and subcontracting opportunities relevant to Zoom Al Arab's capabilities.

The system considers:

- DIRECT opportunities where Zoom could contract with the buyer.
- INDIRECT opportunities where a project, award, or main-contractor signal may create a subcontracting or JV opportunity.

## Core capabilities

- MEP
- HVAC
- VRF
- Chillers
- Chilled water networks
- Firefighting
- Plumbing and drainage
- Electrical power distribution
- Low-current systems
- Infrastructure
- Industrial piping
- Mechanical works
- Maintenance

## Current sources

- Etimad
- Forsah
- NHC Procurement
- TenderSA

## Planned workflow

1. Crawl configured opportunity sources.
2. Identify potentially relevant content.
3. Extract structured opportunity information.
4. Score opportunities against Zoom Al Arab's commercial profile.
5. Generate an opportunity-intelligence digest.
6. Email the digest to configured recipients.

## Configuration

Business profile, source configuration, scoring rubric, recipients, and application settings are stored under `config/`.

Secrets such as API keys, SMTP passwords, and Streamlit secrets must never be committed to GitHub.

## Status

Version 0.1 — development/testing.
