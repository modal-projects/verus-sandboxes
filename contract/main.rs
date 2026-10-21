use vstd::prelude::*;

mod spec;
mod candidate;

vstd::prelude::verus! {

// Require the submitted type to implement the trusted contract.
fn evaluate(v: &Vec<u64>) -> u64
    requires
        v.len() > 0,
{
    <candidate::Candidate as spec::Maximum>::maximum(v)
}

fn main() {}

}
