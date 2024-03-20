First, [install poetry](https://python-poetry.org/)

From the root of this repository,

```
poetry install --with dev
```

## Testing

The unit tests can be run on a Mac, Linux, or Windows computer with a bluetooth adapter.

Since we need access to a hardware bluetooth adapter, these tests can't be run in a typical CI/CD Github Actions-type testing environment.

Run tests:
```
poetry run pytest
```

## Style $ Linting

Use [Black](https://github.com/psf/black) to style all Python code:
```
poetry run black .
```

Run [Pylint](https://pylint.readthedocs.io/en/stable/) to get more detailed feedback.
```
poetry run pylint bleak_fsm/bleak_model.py
```