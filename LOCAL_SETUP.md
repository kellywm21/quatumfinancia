# Local Setup Notes

This project can run locally using the Python installation at:

`C:\Users\Advancia Payledger\AppData\Local\Programs\Python\Python311\python.exe`

## Required packages

Install dependencies from `requirements.txt`:

```powershell
& "C:\Users\Advancia Payledger\AppData\Local\Programs\Python\Python311\python.exe" -m pip install -r requirements.txt
```

## Local test environment

The project now supports local mock Lithic mode without a real Lithic API key.

- Set `USE_MOCK_LITHIC=true`
- Leave `LITHIC_API_KEY=` blank for local development

Pydantic settings now accept an empty `LITHIC_API_KEY` value, and the Lithic client falls back to local mock behavior.

## Run tests

```powershell
& "C:\Users\Advancia Payledger\AppData\Local\Programs\Python\Python311\python.exe" -m pytest -q
```

## Verified working

- `pytest` passes: `17 passed`
- `annotated_types` installed successfully
- Local Python runtime used: `C:\Users\Advancia Payledger\AppData\Local\Programs\Python\Python311\python.exe`
