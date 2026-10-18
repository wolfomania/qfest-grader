from itertools import combinations, islice

import numpy as np
import pytest

from qfest_grader.answers import AnswerError
from qfest_grader.challenges.warsaw_2026 import lab4b


def snake(row):
    """A 26-qubit path through FakeMiami rows row..row+2 (q = 10 * row + col)."""
    return list(range(10 * row, 10 * row + 10)) + list(range(10 * row + 19, 10 * row + 9, -1)) + list(
        range(10 * row + 20, 10 * row + 26))


def test_ex1a_reports_symmetry_start_and_steps():
    assert lab4b._ex1a_answer([(p, p) for p in range(1, 21)]) == {"count": 20, "symmetric": True, "start": 1, "steps": [1]}
    assert lab4b._ex1a_answer([(p, p) for p in range(0, 20, 4)])["steps"] == [4]
    assert lab4b._ex1a_answer([(p, p + 1) for p in range(20)])["symmetric"] is False
    with pytest.raises(AnswerError, match="index pairs"):
        lab4b._ex1a_answer([(1, 2, 3)])


def test_ex1b_checks_chains_and_transpiles_the_test_circuit():
    pytest.importorskip("qiskit_ibm_runtime")
    pairs = [(p, p) for p in range(20)]
    facts = lab4b._ex1b_answer((snake(0) + snake(6), pairs, 0))
    assert facts["chain_a"] and facts["chain_b"] and facts["length"] == 52 and facts["num_pairs"] == 20
    assert isinstance(facts["depth2q"], int) and facts["depth2q"] > 0
    identity = lab4b._ex1b_answer((list(range(52)), pairs, 0))
    assert identity["chain_a"] is False or identity["chain_b"] is False
    short = lab4b._ex1b_answer((snake(0), pairs, 0))
    assert short["length"] == 26 and short["depth2q"] is None
    layout = snake(0) + snake(6)
    assert lab4b._ex1b_answer((layout, pairs, None)) == lab4b._ex1b_answer((layout, pairs, lab4b._TEST_SEED))


def test_test_inputs_are_deterministic():
    assert np.array_equal(lab4b.make_bits((5, 4), 0.5, 1), lab4b.make_bits((5, 4), 0.5, 1))
    assert lab4b.make_floats((2, 3), 7).shape == (2, 3)


def test_ex2a_sends_the_reshaped_test_rows():
    raw = np.zeros((10, 52), dtype=bool)
    facts = lab4b._ex2a_answer((lambda b, n: b.reshape(-1, 2, n), raw))
    assert facts["test_shape"] == [25, 2, 6] and len(facts["test_rows"]) == 25 and facts["raw_block_shape"] == [2, 26]
    flat = lab4b._ex2a_answer((lambda b, n: b, raw))
    assert flat["test_rows"] is None and flat["raw_block_shape"] == [52]


def test_ex2b_and_ex3a_evaluate_the_functions():
    facts = lab4b._ex2b_answer(lambda b: np.sum(~b, axis=-1))
    assert facts["shape"] == [25, 2] and all(0 <= w <= 6 for row in facts["weights"] for w in row)
    values = lab4b._ex3a_answer(lambda occ: occ ** 2)["values"]
    assert len(values) == 240 and all(0 <= v <= 1 for v in values)
    with pytest.raises(AnswerError, match="one weight per orbital"):
        lab4b._ex3a_answer(lambda occ: np.sum(occ))


def test_greedy_generator_returns_the_most_probable_items():
    gen = lab4b.GreedyGenerator(0)
    assert isinstance(gen, np.random.Generator) and np.random.default_rng(gen) is gen
    assert list(gen.choice(np.array([4, 7, 9]), size=2, replace=False, p=[0.2, 0.5, 0.3])) == [7, 9]
    assert gen.choice(np.array([4, 7]), p=[0.5, 0.5]) == 4
    assert gen.choice(3) == 0
    with pytest.raises(ValueError, match="non-negative"):
        gen.choice([1, 2], p=[1.5, -0.5])
    assert 0 <= gen.random() < 1


def recover_lowest(bitstrings, probs, occupancy, num_orbitals, num_elec, rand_seed):
    """Fills or empties the lowest-index orbitals and ignores the occupancies."""
    out = bitstrings.copy()
    for bs, weight in zip(out, np.sum(bitstrings, axis=-1)):
        for i in range(2):
            if weight[i] < num_elec[i]:
                bs[i][np.where(~bs[i])[0][: num_elec[i] - weight[i]]] = True
            elif weight[i] > num_elec[i]:
                bs[i][np.where(bs[i])[0][: weight[i] - num_elec[i]]] = False
    return out, probs


def test_ex3b_rows_are_sorted_and_have_the_right_weights():
    facts = lab4b._ex3b_answer(recover_lowest)
    rows = facts["rows"]
    assert facts["valid"] is True
    assert rows == sorted(rows) and abs(sum(f for _, f in rows) - 1) < 1e-9
    assert all(row[:12].count("1") == 6 and row[12:].count("1") == 6 for row, _ in rows)
    with pytest.raises(AnswerError, match="bitstrings, probabilities"):
        lab4b._ex3b_answer(lambda *args: None)


def test_ex3b_accepts_default_rng_of_rand_seed():
    def recover_with_rng(*args):
        assert np.random.default_rng(args[-1]) is args[-1]
        return recover_lowest(*args)

    assert lab4b._ex3b_answer(recover_with_rng) == lab4b._ex3b_answer(recover_lowest)


def test_ex4_facts_of_the_hf_like_strings():
    ints = [sum(1 << p for p in c) for c in islice(combinations(range(26), 5), 300)]
    facts = lab4b._ex4_answer(np.array([ints, ints]))
    assert facts["shape"] == [2, 300] and facts["rows_equal"] and facts["popcounts"] == [5]
    assert facts["ascending"] is False and lab4b._ex4_answer(np.sort([ints, ints]))["ascending"] is True
    assert lab4b._ex4_answer(np.array([ints[::-1], ints]))["rows_equal"] is False
    assert lab4b._ex4_answer(np.array([1.5, 2.5])) == {"shape": [2]}
    with pytest.raises(AnswerError, match="integer CI strings"):
        lab4b._ex4_answer(np.array([ints, ints], dtype=float))


def test_exbonus_skips_oversized_subspaces():
    big = np.arange(301)
    assert lab4b._exbonus_answer((-108.8, (big, big))) == {"dims": [301, 301], "energy": None, "matches": False}
    with pytest.raises(AnswerError, match="integer array"):
        lab4b._exbonus_answer((-108.8, (np.array([1.5]), np.array([1]))))


def test_exbonus_recomputes_the_hartree_fock_energy():
    pytest.importorskip("pyscf")
    pytest.importorskip("qiskit_addon_sqd")
    hf = np.array([31])
    facts = lab4b._exbonus_answer((-108.330583, (hf, hf)))
    assert facts["dims"] == [1, 1] and facts["matches"] and abs(facts["energy"] + 108.330583) < 1e-5


@pytest.mark.parametrize("strings, error", [
    ([47, 31], "ascending"), ([31, 31, 47], "ascending"), ([7], "5 of the 26"), ([-31], "5 of the 26"),
    ([31 << 22], "5 of the 26"),
])
def test_exbonus_rejects_invalid_ci_strings(strings, error):
    pytest.importorskip("pyscf")
    pytest.importorskip("qiskit_addon_sqd")
    with pytest.raises(AnswerError, match=error):
        lab4b._exbonus_answer((-108.3, (np.array(strings), np.array([31]))))
