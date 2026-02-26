# Project Design

## Repository Structure

### Main package

The package is rooted a `src/docs_buddy`.

The structure underneath the package is as follows:

#### domain

Domain entities, events and commands reside here.

#### services

The use-case layer resides here. It includes usecase handlers.

#### adapters

These wrap connectors to infrastructure and external services

#### entrypoints

These are the endpoints exposed to the external world.

### Tests

Tests are structured as follows:

#### unit

Tests for the domain, services and common functionality

#### integration

Tests that interact with infrastructure

#### e2e

End to end tests that test functionality at the endpoints
