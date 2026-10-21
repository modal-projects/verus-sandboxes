use vstd::prelude::*;

verus! {

pub struct Candidate;

impl crate::spec::Maximum for Candidate {
    fn maximum(v: &Vec<u64>) -> (m: u64) {
        let mut m = v[0];
        let mut i: usize = 1;
        while i < v.len()
            invariant
                1 <= i <= v.len(),
                forall|j: int| 0 <= j < i ==> v[j] <= m,
                exists|j: int| 0 <= j < i && v[j] == m,
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
