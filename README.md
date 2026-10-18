# qfest-grader

Grader client for the Qiskit Fall Fest 2026 Warsaw lab notebooks. It checks your lab answers and records which exercises you completed. The organisers issue participation certificates from these records.

## Install

Run in a notebook cell (Google Colab, Jupyter or VS Code), then restart the kernel:

```python
%pip install -q qfest-grader
```

The install needs Python 3.9 or later. Update an existing install with `%pip install -U qfest-grader`.

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
- circuits as their qubit count, depth, the qubits of each multi-qubit gate and their final state;
- runtime options as the settings the exercise checks;
- job results as the values the exercise checks;
- functions as their outputs on fixed test inputs;
- long lists of numbers as a SHA-256 digest.

Source code and notebook contents are never sent. The email is stored in `~/.qfest/grader.json`, readable only by you.

Some checks run on your machine before sending. Lab 4a Exercise 3c compares your circuit with `annotated_qaoa_ansatz` of your Hamiltonian. Lab 4b Exercise 1b transpiles a test circuit on `FakeMiami`. The Lab 4b bonus recomputes the energy of your subspace, which takes up to two minutes.

## Develop

```bash
pip install -e ".[test,labs]"
pytest
```

Releases go to [PyPI](https://pypi.org/project/qfest-grader/) from GitHub Actions: set the same version in `pyproject.toml` and `qfest_grader/__init__.py`, push, then push the tag `v<version>`.

## Licence

Apache License 2.0. Derived from IBM's [Quantum Challenge Grader](https://github.com/qiskit-community/Quantum-Challenge-Grader); see `NOTICE`.
