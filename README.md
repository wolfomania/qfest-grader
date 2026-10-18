# qfest-grader

Grader client for the Qiskit Fall Fest 2026 Warsaw lab notebooks. It checks your lab answers and records which exercises you completed. The organisers issue participation certificates from these records.

## Install

Run in a notebook cell (Google Colab, Jupyter or VS Code), then restart the kernel:

```python
%pip install -q "qfest-grader @ https://github.com/wolfomania/qfest-grader/archive/refs/heads/main.zip"
```

The install needs Python 3.9 or later and does not need git.

## Use

Save the email you registered with. Run this once per environment; a new Colab session needs it again:

```python
from qfest_grader import save_account
save_account("<your email>")
```

Grade an exercise and check your progress:

```python
from qfest_grader.challenges.warsaw_2026 import check_progress, grade_lab0_ex2

grade_lab0_ex2(counts)
check_progress("lab0")
```

Without a saved account, the grader reads the `QFEST_EMAIL` environment variable.

## What is sent

Each grade call sends your email and a small summary of your answer to the grading server:

- counts, numbers and dictionaries as they are;
- statevectors as their non-zero amplitudes;
- circuits as their qubit count, depth, the qubits of each multi-qubit gate and their final state.

Circuit source code and notebook contents are never sent. The email is stored in `~/.qfest/grader.json`, readable only by you.

## Develop

```bash
pip install -e ".[test]"
pytest
```

## Licence

Apache License 2.0. Derived from IBM's [Quantum Challenge Grader](https://github.com/qiskit-community/Quantum-Challenge-Grader); see `NOTICE`.
