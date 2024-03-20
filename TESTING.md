# Testing

The unit tests can be run on a Mac, Linux, or Windows computer with a bluetooth adapter.

Since we need access to a hardware bluetooth adapter, these tests can't be run in a typical CI/CD Github Actions-type testing environment.

First, [install poetry](https://python-poetry.org/)

From the root of this repository,

```
poetry install --with dev
```

Run tests:
```
poetry run pytest
```
