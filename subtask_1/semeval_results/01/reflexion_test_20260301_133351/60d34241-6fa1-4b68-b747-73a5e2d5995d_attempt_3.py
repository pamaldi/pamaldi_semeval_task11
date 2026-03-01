% COUNTEREXAMPLE: All premises are true but conclusion is false
% The syllogism is INVALID because of undistributed middle term
% All machines are animals (A-type)
% No animals are computers (E-type)
% Conclusion: Some computers are not machines (O-type) ← INVALID

% Create a computer that is NOT a machine (this is what the conclusion claims)
computer(c1).

% Make all machines also animals (as per first premise)
machine(m1).
animal(m1).

% Rule from first premise: All machines are animals
animal(X) :- machine(X).

% Rule from second premise: No animals are computers
conflict :- animal(X), computer(X).

% Validity check: Some computers are NOT machines
% This should FAIL to prove the syllogism is INVALID
valid_syllogism :- computer(X), \+ machine(X).