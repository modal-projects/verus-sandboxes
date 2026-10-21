use vstd::prelude::*;

verus! {

pub struct Candidate;

impl crate::spec::Maximum for Candidate {
    fn maximum(v: &Vec<u64>) -> (m: u64) {
        let mut m = v[0];
        let mut i: usize = 1;
        while i < v.len()
            // TODO: add the invariants needed to prove the contract.
            decreases v.len() - i,
        {
            if v[i] > m {
                m = v[i];
            }
            i = i + 1;
        }
        m
    }
}

}
