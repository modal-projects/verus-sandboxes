use vstd::prelude::*;

vstd::prelude::verus! {

pub trait Maximum {
    fn maximum(v: &Vec<u64>) -> (m: u64)
        requires
            v.len() > 0,
        ensures
            forall|j: int| 0 <= j < v.len() ==> v[j] <= m,
            exists|j: int| 0 <= j < v.len() && v[j] == m;
}

}
