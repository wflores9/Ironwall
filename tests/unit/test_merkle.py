"""Unit tests for InputMerkleTree and verify_proof()."""

import pytest

from ironwall.merkle_audit.tree import InputMerkleTree, verify_proof

SESSION_KEY = b"testsessionkey32bytesexactly!!!!"


def make_tree(n: int) -> InputMerkleTree:
    t = InputMerkleTree()
    for i in range(n):
        t.record_input(ts=i * 1_000_000, data=f"input_{i}".encode(), session_key=SESSION_KEY)
    return t


class TestRecordInput:
    def test_single_leaf(self):
        t = InputMerkleTree()
        leaf = t.record_input(ts=1000, data=b"click", session_key=SESSION_KEY)
        assert len(leaf) == 64  # SHA3-256 hex
        assert len(t) == 1

    def test_multiple_leaves(self):
        t = make_tree(5)
        assert len(t) == 5

    def test_different_keys_produce_different_leaves(self):
        t1 = InputMerkleTree()
        t2 = InputMerkleTree()
        key2 = b"other_key_32_bytes_exactly______"
        l1 = t1.record_input(ts=1, data=b"x", session_key=SESSION_KEY)
        l2 = t2.record_input(ts=1, data=b"x", session_key=key2)
        assert l1 != l2


class TestRoot:
    def test_empty_raises(self):
        with pytest.raises(ValueError):
            InputMerkleTree().root()

    def test_single_leaf_root_equals_leaf(self):
        t = make_tree(1)
        assert t.root() == t.leaves[0]

    def test_power_of_two(self):
        t = make_tree(4)
        root = t.root()
        assert isinstance(root, str)
        assert len(root) == 64

    def test_odd_length_tree(self):
        t = make_tree(3)
        root = t.root()
        assert len(root) == 64

    def test_root_deterministic(self):
        t1 = make_tree(4)
        t2 = make_tree(4)
        assert t1.root() == t2.root()

    def test_different_inputs_different_roots(self):
        t1 = make_tree(4)
        t2 = InputMerkleTree()
        for i in range(4):
            t2.record_input(ts=i * 1_000_000, data=f"OTHER_{i}".encode(), session_key=SESSION_KEY)
        assert t1.root() != t2.root()


class TestProof:
    @pytest.mark.parametrize("n,idx", [
        (1, 0),
        (2, 0), (2, 1),
        (4, 0), (4, 2), (4, 3),
        (5, 0), (5, 4),  # odd tree
        (8, 7),
    ])
    def test_proof_verifies(self, n: int, idx: int):
        t = make_tree(n)
        root = t.root()
        proof = t.generate_proof(idx)
        assert verify_proof(t.leaves[idx], proof, root)

    def test_tampered_leaf_fails(self):
        t = make_tree(4)
        root = t.root()
        proof = t.generate_proof(0)
        assert not verify_proof("a" * 64, proof, root)

    def test_wrong_root_fails(self):
        t = make_tree(4)
        proof = t.generate_proof(0)
        assert not verify_proof(t.leaves[0], proof, "b" * 64)

    def test_out_of_range_raises(self):
        t = make_tree(2)
        with pytest.raises(IndexError):
            t.generate_proof(5)
