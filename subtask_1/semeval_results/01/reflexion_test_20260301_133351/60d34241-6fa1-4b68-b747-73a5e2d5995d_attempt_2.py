% COUNTEREXAMPLE: All premises are true but conclusion is false
% The syllogism is INVALID because of undistributed middle term
% All machines are animals (A-type)
% No animals are computers (E-type)
% Conclusion: Some computers are not machines (O-type) ← INVALID

% Create a computer that is a machine through the chain
computer(c1).
machine(c1).

% Rule from first premise: All machines are animals
animal(X) :- machine(X).

% Rule from second premise: No animals are computers
conflict :- animal(X), computer(X).

% Validity check: Some computers are NOT machines
% This should FAIL to prove the syllogism is INVALID
valid_syllogism :- computer(X), \+ machine(X).