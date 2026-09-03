# Decision

Use Next.js, FastAPI, PostgreSQL, and Docker Compose as the MVP service foundation.

## Context

ChangeProof needs a demonstrable web workflow, typed APIs, persistent evidence, and reproducible local execution across developer environments.

## Options

- A single full-stack JavaScript service
- Next.js with a Python FastAPI analysis service
- A Python-rendered server application

## Decision

Use Next.js for the interface, FastAPI and Pydantic for analysis APIs, PostgreSQL for product data, and Docker Compose for orchestration.

## Reason

Python has strong SQL, subprocess, and AI tooling, while Next.js supports rapid interaction design. Explicit service boundaries keep analysis independent from presentation and Compose makes the baseline reproducible.

## Consequences

The repository has two dependency ecosystems. API contracts must remain typed and versioned. Local native development needs both Node.js and Python, while Docker is the canonical full-stack path.
